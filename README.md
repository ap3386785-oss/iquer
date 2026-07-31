# Aegis Spirit: AI-Based Smart Alcohol Purchase Verification & Limit System

This is a complete, feature-rich web application built with **Python (Flask)**, **OpenCV**, **MySQL (with SQLite fallback)**, and **HTML5/CSS3/JavaScript**.

---

## Features
1. **Live Face Recognition & Age Verification**: Uses the laptop webcam to scan a customer's face, matches it against their registered profile, calculates age from DOB, and displays an "Eligible" or "Not Eligible" warning.
2. **Purchase Limit Enforcement**: Automatically monitors and updates weekly (180 ml) and monthly (920 ml) limits. Blocks transactions if the limit is exceeded.
3. **Double Face Verification**: Performs initial scan for checking limits, and a final checkout face verification when the owner clicks "Submit" to complete the purchase.
4. **Owner Analytics Dashboard**: Features cards for daily metrics, interactive weekly and monthly charts, and real-time event logs.
5. **AI Risk Alerts**: Detects and flags:
   - Repeated face verification failures (security warnings).
   - Underage purchase attempts.
   - Multiple purchases made by the same customer in one day.
   - Purchase attempts from multiple shops within 30 minutes (simulated travel detection).
6. **Detailed Purchase History**: View complete transaction histories and remaining limits for any customer.

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.8+** installed on your system.
- **MySQL Server** (Optional: the system automatically falls back to **SQLite** if MySQL is not running, creating a local file `smart_alcohol.db` for instant testing).

### 2. Install Python Dependencies
Open your command terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

### 3. (Optional) Setup MySQL Database
If you prefer to use MySQL rather than the SQLite auto-fallback:
1. Start your local MySQL Server.
2. The database schema is located at `database/schema.sql`. You can run this script to create the database:
   ```sql
   SOURCE database/schema.sql;
   ```
3. Update your credentials at the top of [db_helper.py](file:///m:/iquer/backend/db_helper.py):
   ```python
   DB_HOST = "localhost"
   DB_USER = "root"
   DB_PASSWORD = "your_mysql_password_here"
   DB_NAME = "smart_alcohol_system"
   ```

### 4. Running the Application
Launch the Flask development server:
```bash
python backend/app.py
```
Open your browser and navigate to: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Sandbox / Developer Testing Quick Guide
To make testing quick and easy without registering multiple individuals:
1. **Register Panel**: Go to the *Register Customer* page, and click **Populate Demo Customers** at the bottom. This will automatically load the database with 4 mock customers:
   - `Aarav Sharma` (Adult, has 1 previous purchase)
   - `Ananya Patel` (Adult, no previous purchases)
   - `Rohan Verma` (Underage minor - Age 16)
   - `Priya Nair` (Adult, no previous purchases)
2. **Face Scanner fallback**:
   - The AI face verifier uses a dual-method approach: it attempts to load the standard `face_recognition` library, but falls back to a structural features matcher using OpenCV's ORB keypoint comparisons if CMake/dlib is not compiled on your OS.
   - You can toggle the **Force Face Verification Fail** checkbox in the Developer Sandbox at the bottom of the checkout page to simulate a verification mismatch. This lets you inspect limit blocking behavior and view the resulting **AI Risk Alerts** on the dashboard.
