# Flask Backend Server
import sys
import os
# Add parent directory to sys.path to resolve module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, redirect, url_for
from db_helper import DatabaseHelper
from ai_modules.face_verifier import FaceVerifier
from ai_modules.ocr_extractor import OCRExtractor
import os
import re
import datetime
import base64
import random

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database, face verifier, and OCR extractor
db = DatabaseHelper()
verifier = FaceVerifier()
ocr_extractor = OCRExtractor()

# Ensure id_photo_path column exists (migration for existing DBs)
try:
    import sqlite3
    _mig_conn = sqlite3.connect(db.sqlite_path)
    _mig_conn.execute("ALTER TABLE customers ADD COLUMN id_photo_path TEXT NULL")
    _mig_conn.commit()
    _mig_conn.close()
    print("[INFO] Migration: added id_photo_path column.")
except Exception:
    pass  # Column already exists or not using SQLite

# Helper to calculate age from DOB string (YYYY-MM-DD)
def calculate_age(dob_str):
    try:
        dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        # Adjust for local time if necessary, using today
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except Exception as e:
        print(f"[ERROR] Age calculation error: {e}")
        return 0

# Page Routes
@app.route('/')
@app.route('/terminal')
def terminal_page():
    shops = db.get_shops()
    customers = db.get_all_customers()
    return render_template('index.html', title="POS Terminal", shops=shops, customers=customers)

@app.route('/register')
def register_page():
    return render_template('register.html', title="Customer Registration")

@app.route('/dashboard')
def dashboard_page():
    shops = db.get_shops()
    return render_template('dashboard.html', title="Owner Dashboard", shops=shops)

# API Endpoints

@app.route('/api/shops', methods=['GET'])
def api_get_shops():
    return jsonify(db.get_shops())

@app.route('/api/customers', methods=['GET'])
def api_get_customers():
    return jsonify(db.get_all_customers())

@app.route('/api/register_customer', methods=['POST'])
def api_register_customer():
    temp_files = []  # track temp files for cleanup on error
    try:
        id_type = request.form.get('id_type', '').strip()
        if not id_type:
            return jsonify({"success": False, "message": "ID type is required."}), 400

        photo_file   = request.files.get('photo_file')   # uploaded profile photo
        live_photo   = request.form.get('live_photo')    # base64 webcam capture
        id_photo_file = request.files.get('id_photo_file')  # Aadhaar / DL scan

        # ── Require at least one photo for the customer's profile ──────────
        if not (photo_file and photo_file.filename) and not live_photo:
            return jsonify({"success": False, "message": "Please upload a profile photo or capture a live webcam photo."}), 400

        # ── Require the ID document ────────────────────────────────────────
        if not (id_photo_file and id_photo_file.filename):
            return jsonify({"success": False, "message": "Please upload your government ID document (Aadhaar/DL scan)."}), 400

        uid = str(random.randint(10000000, 99999999))

        # ── Step 1: Save profile photo (prefer uploaded file over webcam) ──
        profile_filename = f"profile_temp_{uid}.jpg"
        profile_path = os.path.join(UPLOAD_FOLDER, profile_filename)

        if photo_file and photo_file.filename:
            photo_file.save(profile_path)
        else:
            # Save webcam base64
            b64 = live_photo.split(',')[1] if ',' in live_photo else live_photo
            with open(profile_path, 'wb') as fh:
                fh.write(base64.b64decode(b64))
        temp_files.append(profile_path)

        # ── Step 2: Save ID document ───────────────────────────────────────
        id_filename = f"id_doc_temp_{uid}.jpg"
        id_path = os.path.join(UPLOAD_FOLDER, id_filename)
        id_photo_file.save(id_path)
        temp_files.append(id_path)

        # ── Step 3: Face verification (webcam vs profile photo) ────────────
        if live_photo:
            matched, confidence, face_detected = verifier.verify_faces(profile_path, live_photo)
            if not face_detected:
                return jsonify({"success": False, "message": "No face detected in your live webcam photo. Please capture a clear, well-lit selfie."}), 400
            if not matched:
                return jsonify({"success": False, "message": f"Face verification failed (confidence: {confidence:.0f}%). Please ensure the webcam matches your profile photo."}), 400
            print(f"[INFO] Face verification passed — confidence: {confidence:.1f}%")
        else:
            print("[INFO] No live photo provided — skipping face verification.")

        # ── Step 4: OCR — extract identity details from ID document ────────
        extracted = ocr_extractor.extract_id_info(id_path)
        # extract_id_info always returns a valid dict (never None)
        name      = extracted['name']
        id_number = extracted['id_number']
        dob       = extracted['dob']

        # ── Step 5: Age check (must be 18+) ───────────────────────────────
        age = calculate_age(dob)
        if age < 18:
            return jsonify({"success": False, "message": f"Registration denied: customer is underage ({age} years old). Minimum age is 18."}), 400

        # ── Step 6: Duplicate check ────────────────────────────────────────
        if db.get_customer_by_id_number(id_number):
            return jsonify({"success": False, "message": f"A customer with this {id_type} number is already registered."}), 400

        # ── Step 7: Rename temp files to final names ───────────────────────
        safe_id = re.sub(r'[^A-Za-z0-9]', '_', id_number)
        final_profile = os.path.join(UPLOAD_FOLDER, f"profile_{safe_id}.jpg")
        final_id      = os.path.join(UPLOAD_FOLDER, f"id_doc_{safe_id}.jpg")

        os.replace(profile_path, final_profile)
        os.replace(id_path, final_id)
        temp_files.clear()  # files moved — no cleanup needed

        db_photo_path    = f"uploads/profile_{safe_id}.jpg"
        db_id_photo_path = f"uploads/id_doc_{safe_id}.jpg"

        # ── Step 8: Persist to database ────────────────────────────────────
        customer_id = db.register_customer(name, id_number, id_type, dob, db_photo_path, db_id_photo_path)

        return jsonify({
            "success": True,
            "message": "Customer registered successfully!",
            "customer_id": customer_id,
            "extracted": {
                "name": name,
                "id_number": id_number,
                "dob": dob,
                "age": age
            }
        })

    except Exception as e:
        import traceback
        print(f"[ERROR] Registration exception:\n{traceback.format_exc()}")
        # Clean up any temp files on error
        for f in temp_files:
            try:
                os.remove(f)
            except Exception:
                pass
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route('/api/verify_customer_face', methods=['POST'])
def api_verify_customer_face():
    try:
        data = request.json
        customer_id = data.get('customer_id')
        shop_id = data.get('shop_id')
        live_image = data.get('live_image') # base64 string
        force_fail = data.get('force_fail', False)

        if not shop_id or not live_image:
            return jsonify({"success": False, "message": "Shop ID and live camera snapshot are required."}), 400

        customer = None
        # Support 1:1 match if customer_id is provided, otherwise search all for a match (1:N)
        if customer_id:
            customer = db.get_customer_by_id(customer_id)
        else:
            # 1:N Face Recognition search across all registered customers
            all_customers = db.get_all_customers()
            for c_info in all_customers:
                cust_details = db.get_customer_by_id(c_info['id'])
                if not cust_details:
                    continue
                baseline_path = os.path.join(app.static_folder, cust_details['photo_path'])
                matched, conf, detected = verifier.verify_faces(baseline_path, live_image, force_fail)
                if matched:
                    customer = cust_details
                    break

        if not customer:
            # Increment face failure without specific customer
            db.log_face_failure(None, shop_id)
            recent_failures = db.count_recent_face_failures(None, shop_id, minutes=5)
            if recent_failures >= 3:
                db.add_alert(None, shop_id, 'repeated_face_failures', 
                             f"Security Warning: 3 consecutive face recognition failures detected at this counter within 5 minutes.")
            
            return jsonify({
                "success": False, 
                "message": "Face verification failed. Customer identity could not be verified.",
                "reason": "face_mismatch"
            })

        # Perform verification for the selected customer
        baseline_path = os.path.join(app.static_folder, customer['photo_path'])
        matched, confidence, face_detected = verifier.verify_faces(baseline_path, live_image, force_fail)

        if not face_detected:
            return jsonify({
                "success": False, 
                "message": "No face detected in live video feed. Please align your face with the camera.",
                "reason": "no_face_detected"
            })

        if not matched:
            # Log face failure for this customer
            db.log_face_failure(customer['id'], shop_id)
            recent_failures = db.count_recent_face_failures(customer['id'], shop_id, minutes=5)
            if recent_failures >= 3:
                db.add_alert(customer['id'], shop_id, 'repeated_face_failures', 
                             f"Security Alert: Face verification failed 3+ times for customer {customer['name']} (ID: {customer['id_number']}) at this shop counter.")
            
            return jsonify({
                "success": False, 
                "message": f"Face verification failed. Image does not match registered photo for {customer['name']}.",
                "reason": "face_mismatch",
                "confidence": confidence
            })

        # Calculate customer age
        age = calculate_age(customer['dob'])
        if age < 18:
            # Log AI alert for underage purchase attempt
            db.add_alert(customer['id'], shop_id, 'under_18_attempt', 
                         f"Underage Attempt: {customer['name']} (Age {age}, DOB {customer['dob']}) attempted to purchase alcohol.")
            return jsonify({
                "success": True,
                "eligible": False,
                "reason": "under_18",
                "message": f"Not Eligible: Customer is under 18 years of age (Current age: {age}).",
                "customer": customer,
                "age": age,
                "confidence": confidence
            })

        # If eligible, fetch limits
        limits = db.calculate_limits(customer['id'])
        
        return jsonify({
            "success": True,
            "eligible": True,
            "message": "Customer verified. Eligible for purchase.",
            "customer": customer,
            "age": age,
            "limits": limits,
            "confidence": confidence
        })
    except Exception as e:
        print(f"[ERROR] Face verification exception: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/submit_purchase', methods=['POST'])
def api_submit_purchase():
    try:
        data = request.json
        customer_id = data.get('customer_id')
        shop_id = data.get('shop_id')
        quantity = int(data.get('quantity', 0))
        live_image = data.get('live_image') # base64 string for final verification
        force_fail = data.get('force_fail', False)

        if not customer_id or not shop_id or not quantity or not live_image:
            return jsonify({"success": False, "message": "All fields including checkout face confirmation are required."}), 400

        customer = db.get_customer_by_id(customer_id)
        if not customer:
            return jsonify({"success": False, "message": "Customer not found."}), 404

        # 1. Final Face Verification Check
        baseline_path = os.path.join(app.static_folder, customer['photo_path'])
        matched, confidence, face_detected = verifier.verify_faces(baseline_path, live_image, force_fail)

        if not face_detected or not matched:
            db.log_face_failure(customer_id, shop_id)
            db.add_alert(customer_id, shop_id, 'repeated_face_failures', 
                         f"Checkout Warning: Final transaction face verification failed for customer {customer['name']} during submit.")
            return jsonify({
                "success": False, 
                "message": "Final checkout face verification failed. Purchase transaction blocked for security.",
                "reason": "checkout_face_failed"
            })

        # 2. Check Age (Double security check)
        age = calculate_age(customer['dob'])
        if age < 18:
            return jsonify({"success": False, "message": "Transaction blocked. Customer is under 18 years.", "reason": "under_18"}), 403

        # 3. Check Limits
        limits = db.calculate_limits(customer_id)
        
        if quantity > limits['remaining_weekly'] or quantity > limits['remaining_monthly']:
            db.add_alert(customer_id, shop_id, 'purchase_limit_exceeded', 
                         f"Limit Overrun: Customer {customer['name']} tried to buy {quantity}ml, which exceeds their remaining weekly ({limits['remaining_weekly']}ml) or monthly ({limits['remaining_monthly']}ml) limit.")
            return jsonify({
                "success": False, 
                "message": "Purchase Limit Reached: Requested quantity exceeds the customer's remaining weekly or monthly purchase limits.",
                "reason": "limit_exceeded"
            }), 400

        # Calculate new remaining limits
        new_remaining_weekly = max(0, limits['remaining_weekly'] - quantity)
        new_remaining_monthly = max(0, limits['remaining_monthly'] - quantity)

        # 4. Record Purchase
        purchase_id = db.record_purchase(customer_id, shop_id, quantity, new_remaining_weekly, new_remaining_monthly)

        # 5. Check AI Risk Alerts
        # Alert A: Multiple purchases in a single day
        # Look at purchases today (2026-07-28)
        purchases_list = db.get_customer_purchases(customer_id)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        today_purchases = [p for p in purchases_list if p['date'] == today_str]
        
        if len(today_purchases) > 1: # This is at least the 2nd purchase today
            db.add_alert(customer_id, shop_id, 'multiple_purchases_today', 
                         f"Suspicious Action: Customer {customer['name']} purchased alcohol {len(today_purchases)} times in a single day.")

        # Alert B: Multiple shop purchase attempts in short period (30 minutes)
        # Check purchases at other shops in the last 30 minutes
        recent_purchases_other_shops = []
        now = datetime.datetime.now()
        for p in purchases_list:
            p_dt = datetime.datetime.strptime(f"{p['date']} {p['time']}", "%Y-%m-%d %H:%M:%S")
            # If within 30 minutes, and different shop_id
            time_diff = (now - p_dt).total_seconds() / 60
            if 0 <= time_diff <= 30 and p['shop_name'] != db.get_shops()[int(shop_id)-1]['name']:
                recent_purchases_other_shops.append(p)
                
        if recent_purchases_other_shops:
            other_shop = recent_purchases_other_shops[0]['shop_name']
            db.add_alert(customer_id, shop_id, 'multi_shop_purchase', 
                         f"Suspicious Action: Customer {customer['name']} purchased from {other_shop} and current shop within 30 minutes.")

        return jsonify({
            "success": True,
            "message": "Purchase successful!",
            "purchase_details": {
                "status": "Purchase Successful",
                "purchased_quantity": quantity,
                "remaining_weekly": new_remaining_weekly,
                "remaining_monthly": new_remaining_monthly,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "time": datetime.datetime.now().strftime("%H:%M:%S")
            }
        })
    except Exception as e:
        print(f"[ERROR] Submit purchase exception: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/dashboard_data', methods=['GET'])
def api_get_dashboard_data():
    try:
        shop_id = request.args.get('shop_id', 1, type=int)
        
        metrics = db.get_dashboard_metrics(shop_id)
        weekly = db.get_weekly_sales_report(shop_id)
        monthly = db.get_monthly_sales_report(shop_id)
        alerts = db.get_active_alerts(limit=10)
        
        return jsonify({
            "success": True,
            "metrics": metrics,
            "weekly_report": weekly,
            "monthly_report": monthly,
            "alerts": alerts
        })
    except Exception as e:
        print(f"[ERROR] Dashboard data exception: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/customer_history/<int:customer_id>', methods=['GET'])
def api_customer_history(customer_id):
    try:
        customer = db.get_customer_by_id(customer_id)
        if not customer:
            return jsonify({"success": False, "message": "Customer not found."}), 404
            
        purchases = db.get_customer_purchases(customer_id)
        limits = db.calculate_limits(customer_id)
        
        return jsonify({
            "success": True,
            "customer": customer,
            "limits": limits,
            "history": purchases
        })
    except Exception as e:
        print(f"[ERROR] Customer history exception: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# Developer Mock routes for demo testing
@app.route('/api/dev/populate', methods=['POST'])
def api_dev_populate():
    try:
        # Check if database already has customers to prevent duplicate populate
        c_count = len(db.get_all_customers())
        if c_count > 0:
            return jsonify({"success": True, "message": "Database already populated with test customers."})
            
        # Create some mock images of colored squares or mock icons and register them
        # In reality, they are small placeholder images we save on disk to represent faces
        mock_faces = [
            {"name": "Aarav Sharma", "id": "123456789012", "type": "Aadhaar Card", "dob": "1995-04-12", "color": (255, 0, 0)}, # Red
            {"name": "Ananya Patel", "id": "987654321098", "type": "Aadhaar Card", "dob": "1990-11-23", "color": (0, 255, 0)}, # Green
            {"name": "Rohan Verma", "id": "DL-55201800123", "type": "Driving Licence", "dob": "2010-06-15", "color": (0, 0, 255)}, # Blue (Under 18)
            {"name": "Priya Nair", "id": "456789012345", "type": "Aadhaar Card", "dob": "2003-08-30", "color": (255, 255, 0)} # Yellow
        ]
        
        for index, face in enumerate(mock_faces):
            filename = f"profile_{face['id']}.jpg"
            photo_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Write a simple BGR color image as their profile photo for testing
            img = np.zeros((300, 300, 3), dtype=np.uint8)
            # Fill with solid color and write name on it to simulate a face photo
            cv2.rectangle(img, (0, 0), (300, 300), face['color'], -1)
            cv2.putText(img, face['name'], (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imwrite(photo_path, img)
            
            # Create a mock Aadhaar/DL document image
            id_filename = f"id_document_{face['id']}.jpg"
            id_photo_path = os.path.join(UPLOAD_FOLDER, id_filename)
            id_img = np.zeros((200, 320, 3), dtype=np.uint8)
            # Fill with light cream background
            id_img[:] = (240, 248, 255)
            # Draw header border
            cv2.rectangle(id_img, (0, 0), (320, 40), (0, 0, 180), -1)
            cv2.putText(id_img, face['type'].upper(), (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(id_img, f"NAME: {face['name']}", (15, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
            cv2.putText(id_img, f"DOB: {face['dob']}", (15, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
            cv2.putText(id_img, f"NUMBER: {face['id']}", (15, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 2)
            cv2.imwrite(id_photo_path, id_img)
            
            dbpath = f"uploads/{filename}"
            db_id_path = f"uploads/{id_filename}"
            db.register_customer(face['name'], face['id'], face['type'], face['dob'], dbpath, db_id_path)
            
        # Add some mock purchase history
        # Customer 1 (Aarav): bought 50ml wines 2 days ago
        aarav = db.get_customer_by_id_number("123456789012")
        if aarav:
            # We record a historic purchase
            db.record_purchase(aarav['id'], 1, 50, 130, 870)
            
        return jsonify({"success": True, "message": "Pre-populated database with 4 mock customers (including 1 minor) successfully."})
    except Exception as e:
        print(f"[ERROR] Pre-populate exception: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    # Running Flask Server on host 0.0.0.0, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
