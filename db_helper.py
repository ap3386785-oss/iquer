# Database helper for MySQL / SQLite fallback
import mysql.connector
from mysql.connector import Error
import sqlite3
import os
import datetime

# Database Configuration (Customize for MySQL)
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "smart_alcohol_system"

class DatabaseHelper:
    def __init__(self):
        self.use_sqlite = False
        self.sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "smart_alcohol.db")
        self.conn = None
        self.try_mysql_connection()

    def try_mysql_connection(self):
        try:
            # Try to connect to MySQL server (without DB first, to create database if not exists)
            temp_conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD
            )
            cursor = temp_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            temp_conn.commit()
            cursor.close()
            temp_conn.close()

            # Now connect to the database
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            self.use_sqlite = False
            print("[INFO] Connected successfully to MySQL Database.")
            self.init_mysql_tables()
        except Exception as e:
            print(f"[WARNING] MySQL connection failed: {e}")
            print(f"[INFO] Falling back to SQLite database at: {self.sqlite_path}")
            self.use_sqlite = True
            self.init_sqlite_tables()

    def get_connection(self):
        if self.use_sqlite:
            # SQLite connection must be thread-safe in Flask, so we open a new one per request or disable thread check
            return sqlite3.connect(self.sqlite_path)
        else:
            try:
                # Check if connection is still active, else reconnect
                if not self.conn or not self.conn.is_connected():
                    self.conn = mysql.connector.connect(
                        host=DB_HOST,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        database=DB_NAME
                    )
                return self.conn
            except Exception as e:
                print(f"[ERROR] MySQL reconnection failed: {e}. Falling back to SQLite temporarily.")
                self.use_sqlite = True
                return sqlite3.connect(self.sqlite_path)

    def init_mysql_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # We can read database/schema.sql and execute it
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute multi-queries
            for result in cursor.execute(schema_sql, multi=True):
                pass
            conn.commit()
        cursor.close()

    def init_sqlite_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # SQLite schema creation
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Insert default shops
        cursor.execute("SELECT COUNT(*) FROM shops")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO shops (name, location) VALUES (?, ?)", [
                ('Main Street Wines', 'Block 1, Downtown'),
                ('Highway Plaza Liquors', 'Mile 4, North Expressway'),
                ('Metro Station Spirits', 'Underground Mall, Central')
            ])

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            id_number TEXT NOT NULL UNIQUE,
            id_type TEXT NOT NULL,
            dob TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            id_photo_path TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            shop_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            remaining_weekly INTEGER NOT NULL,
            remaining_monthly INTEGER NOT NULL,
            purchase_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NULL,
            shop_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            description TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NULL,
            shop_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()

    def execute_query(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Adapt SQL syntax from MySQL to SQLite if needed
        if self.use_sqlite:
            query = query.replace("%s", "?")
            query = query.replace("AUTO_INCREMENT", "AUTOINCREMENT")
        
        try:
            cursor.execute(query, params)
            last_id = cursor.lastrowid
            conn.commit()
            return last_id
        except Exception as e:
            print(f"[ERROR] Database execute query error: {e}")
            raise e
        finally:
            if self.use_sqlite:
                cursor.close()
                conn.close()
            else:
                cursor.close()

    def fetch_all(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_sqlite:
            query = query.replace("%s", "?")
            
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            # If using sqlite, rows are tuples. If MySQL, rows are tuples too (by default).
            return rows
        except Exception as e:
            print(f"[ERROR] Database fetch all error: {e}")
            return []
        finally:
            if self.use_sqlite:
                cursor.close()
                conn.close()
            else:
                cursor.close()

    def fetch_one(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_sqlite:
            query = query.replace("%s", "?")
            
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row
        except Exception as e:
            print(f"[ERROR] Database fetch one error: {e}")
            return None
        finally:
            if self.use_sqlite:
                cursor.close()
                conn.close()
            else:
                cursor.close()

    # Domain Methods

    def register_customer(self, name, id_number, id_type, dob, photo_path, id_photo_path=None):
        query = "INSERT INTO customers (name, id_number, id_type, dob, photo_path, id_photo_path) VALUES (%s, %s, %s, %s, %s, %s)"
        return self.execute_query(query, (name, id_number, id_type, dob, photo_path, id_photo_path))

    def get_customer_by_id(self, customer_id):
        row = self.fetch_one("SELECT id, name, id_number, id_type, dob, photo_path, id_photo_path, created_at FROM customers WHERE id = %s", (customer_id,))
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "id_number": row[2],
                "id_type": row[3],
                "dob": row[4] if isinstance(row[4], str) else row[4].strftime("%Y-%m-%d"),
                "photo_path": row[5],
                "id_photo_path": row[6],
                "created_at": row[7]
            }
        return None

    def get_customer_by_id_number(self, id_number):
        row = self.fetch_one("SELECT id, name, id_number, id_type, dob, photo_path, id_photo_path, created_at FROM customers WHERE id_number = %s", (id_number,))
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "id_number": row[2],
                "id_type": row[3],
                "dob": row[4] if isinstance(row[4], str) else row[4].strftime("%Y-%m-%d"),
                "photo_path": row[5],
                "id_photo_path": row[6],
                "created_at": row[7]
            }
        return None

    def get_all_customers(self):
        rows = self.fetch_all("SELECT id, name, id_number, id_type, dob FROM customers ORDER BY name ASC")
        customers = []
        for r in rows:
            customers.append({
                "id": r[0],
                "name": r[1],
                "id_number": r[2],
                "id_type": r[3],
                "dob": r[4] if isinstance(r[4], str) else r[4].strftime("%Y-%m-%d")
            })
        return customers

    def get_shops(self):
        rows = self.fetch_all("SELECT id, name, location FROM shops")
        return [{"id": r[0], "name": r[1], "location": r[2]} for r in rows]

    def get_customer_purchases(self, customer_id):
        query = """
            SELECT p.id, p.quantity, p.remaining_weekly, p.remaining_monthly, p.purchase_timestamp, s.name 
            FROM purchases p 
            JOIN shops s ON p.shop_id = s.id 
            WHERE p.customer_id = %s 
            ORDER BY p.purchase_timestamp DESC
        """
        rows = self.fetch_all(query, (customer_id,))
        purchases = []
        for r in rows:
            ts = r[4]
            if isinstance(ts, str):
                # SQLite timestamp parsing
                try:
                    dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt = datetime.datetime.now() # Fallback
            else:
                dt = ts
            
            purchases.append({
                "id": r[0],
                "quantity": r[1],
                "remaining_weekly": r[2],
                "remaining_monthly": r[3],
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M:%S"),
                "shop_name": r[5]
            })
        return purchases

    def calculate_limits(self, customer_id):
        # Weekly Limit: 180ml
        # Monthly Limit: 920ml
        WEEKLY_LIMIT = 180
        MONTHLY_LIMIT = 920
        
        # Calculate purchases in the last 7 days (rolling)
        # Note: SQLite vs MySQL date subtraction
        if self.use_sqlite:
            weekly_query = """
                SELECT SUM(quantity) FROM purchases 
                WHERE customer_id = ? 
                AND purchase_timestamp >= datetime('now', '-7 days')
            """
            monthly_query = """
                SELECT SUM(quantity) FROM purchases 
                WHERE customer_id = ? 
                AND purchase_timestamp >= datetime('now', '-30 days')
            """
        else:
            weekly_query = """
                SELECT SUM(quantity) FROM purchases 
                WHERE customer_id = %s 
                AND purchase_timestamp >= NOW() - INTERVAL 7 DAY
            """
            monthly_query = """
                SELECT SUM(quantity) FROM purchases 
                WHERE customer_id = %s 
                AND purchase_timestamp >= NOW() - INTERVAL 30 DAY
            """
            
        w_row = self.fetch_one(weekly_query, (customer_id,))
        m_row = self.fetch_one(monthly_query, (customer_id,))
        
        purchased_weekly = w_row[0] if w_row and w_row[0] is not None else 0
        purchased_monthly = m_row[0] if m_row and m_row[0] is not None else 0
        
        remaining_weekly = max(0, WEEKLY_LIMIT - purchased_weekly)
        remaining_monthly = max(0, MONTHLY_LIMIT - purchased_monthly)
        
        # Previously purchased is the sum of all time purchases
        total_query = "SELECT SUM(quantity) FROM purchases WHERE customer_id = %s"
        t_row = self.fetch_one(total_query, (customer_id,))
        total_purchased = t_row[0] if t_row and t_row[0] is not None else 0
        
        return {
            "previously_purchased": total_purchased,
            "purchased_weekly": purchased_weekly,
            "purchased_monthly": purchased_monthly,
            "remaining_weekly": remaining_weekly,
            "remaining_monthly": remaining_monthly,
            "weekly_limit": WEEKLY_LIMIT,
            "monthly_limit": MONTHLY_LIMIT
        }

    def record_purchase(self, customer_id, shop_id, quantity, remaining_weekly, remaining_monthly):
        query = """
            INSERT INTO purchases (customer_id, shop_id, quantity, remaining_weekly, remaining_monthly)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (customer_id, shop_id, quantity, remaining_weekly, remaining_monthly))

    def log_face_failure(self, customer_id, shop_id):
        query = "INSERT INTO face_failures (customer_id, shop_id) VALUES (%s, %s)"
        return self.execute_query(query, (customer_id, shop_id))

    def count_recent_face_failures(self, customer_id, shop_id, minutes=10):
        if self.use_sqlite:
            query = """
                SELECT COUNT(*) FROM face_failures 
                WHERE shop_id = ? 
                AND (customer_id = ? OR customer_id IS NULL)
                AND timestamp >= datetime('now', '-%s minutes')
            """ % minutes
        else:
            query = """
                SELECT COUNT(*) FROM face_failures 
                WHERE shop_id = %s 
                AND (customer_id = %s OR customer_id IS NULL)
                AND timestamp >= NOW() - INTERVAL %s MINUTE
            """ % (shop_id, customer_id if customer_id else "NULL", minutes)
            
        row = self.fetch_one(query, (shop_id, customer_id) if customer_id else (shop_id,))
        return row[0] if row else 0

    def add_alert(self, customer_id, shop_id, alert_type, description):
        # Prevent logging duplicate active alerts of same type within last 5 minutes to avoid flood
        if self.use_sqlite:
            check_query = """
                SELECT COUNT(*) FROM alerts 
                WHERE shop_id = ? AND alert_type = ? 
                AND (customer_id = ? OR (customer_id IS NULL AND ? IS NULL))
                AND timestamp >= datetime('now', '-5 minutes')
            """
            params = (shop_id, alert_type, customer_id, customer_id)
        else:
            check_query = """
                SELECT COUNT(*) FROM alerts 
                WHERE shop_id = %s AND alert_type = %s 
                AND (customer_id = %s OR (customer_id IS NULL AND %s IS NULL))
                AND timestamp >= NOW() - INTERVAL 5 MINUTE
            """
            params = (shop_id, alert_type, customer_id, customer_id)
            
        row = self.fetch_one(check_query, params)
        if row and row[0] > 0:
            return None # Skip duplicate log
            
        query = """
            INSERT INTO alerts (customer_id, shop_id, alert_type, description)
            VALUES (%s, %s, %s, %s)
        """
        return self.execute_query(query, (customer_id, shop_id, alert_type, description))

    def get_active_alerts(self, limit=20):
        query = """
            SELECT a.id, a.customer_id, a.alert_type, a.description, a.timestamp, s.name, c.name
            FROM alerts a
            JOIN shops s ON a.shop_id = s.id
            LEFT JOIN customers c ON a.customer_id = c.id
            ORDER BY a.timestamp DESC
            LIMIT %s
        """
        rows = self.fetch_all(query, (limit,))
        alerts = []
        for r in rows:
            ts = r[4]
            if isinstance(ts, str):
                try:
                    dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt = datetime.datetime.now()
            else:
                dt = ts
                
            alerts.append({
                "id": r[0],
                "customer_id": r[1],
                "alert_type": r[2],
                "description": r[3],
                "time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "shop_name": r[5],
                "customer_name": r[6] if r[6] else "Unknown/Unverified"
            })
        return alerts

    def get_dashboard_metrics(self, shop_id):
        # Today's Customers (unique customer purchases + verification attempts or alerts today)
        if self.use_sqlite:
            today_purchases_q = "SELECT COUNT(DISTINCT customer_id) FROM purchases WHERE shop_id = ? AND date(purchase_timestamp) = date('now')"
            all_purchases_today_q = "SELECT COUNT(*) FROM purchases WHERE shop_id = ? AND date(purchase_timestamp) = date('now')"
            total_sold_today_q = "SELECT SUM(quantity) FROM purchases WHERE shop_id = ? AND date(purchase_timestamp) = date('now')"
            
            # Eligible/Rejected count can be calculated by looking at purchases vs alerts
            # Let's count unique customers verified eligible vs rejected
            # Customers are marked rejected if they have an alert of type 'under_18' or verification fails
            # For demonstration, let's track the counts based on purchases (eligible) and alerts (rejected/failures)
            rejected_today_q = """
                SELECT COUNT(DISTINCT customer_id) FROM alerts 
                WHERE shop_id = ? AND date(timestamp) = date('now') 
                AND alert_type IN ('under_18_attempt', 'repeated_face_failures', 'purchase_limit_exceeded')
            """
            
        else:
            today_purchases_q = "SELECT COUNT(DISTINCT customer_id) FROM purchases WHERE shop_id = %s AND DATE(purchase_timestamp) = CURDATE()"
            all_purchases_today_q = "SELECT COUNT(*) FROM purchases WHERE shop_id = %s AND DATE(purchase_timestamp) = CURDATE()"
            total_sold_today_q = "SELECT SUM(quantity) FROM purchases WHERE shop_id = %s AND DATE(purchase_timestamp) = CURDATE()"
            rejected_today_q = """
                SELECT COUNT(DISTINCT customer_id) FROM alerts 
                WHERE shop_id = %s AND DATE(timestamp) = CURDATE() 
                AND alert_type IN ('under_18_attempt', 'repeated_face_failures', 'purchase_limit_exceeded')
            """
            
        c_today = self.fetch_one(today_purchases_q, (shop_id,))
        total_sold = self.fetch_one(total_sold_today_q, (shop_id,))
        rejected = self.fetch_one(rejected_today_q, (shop_id,))
        
        eligible_count = c_today[0] if c_today else 0
        rejected_count = rejected[0] if rejected else 0
        total_alcohol_sold = total_sold[0] if total_sold and total_sold[0] is not None else 0
        
        # Today's total unique customers is eligible + rejected
        todays_customers = eligible_count + rejected_count
        
        return {
            "todays_customers": todays_customers,
            "eligible_count": eligible_count,
            "rejected_count": rejected_count,
            "total_alcohol_sold": total_alcohol_sold
        }

    def get_weekly_sales_report(self, shop_id):
        # Returns sales volume for each of the last 7 days
        days = []
        sales = []
        
        for i in range(6, -1, -1):
            if self.use_sqlite:
                date_str_q = "SELECT date('now', '-%d days')" % i
                date_val = self.fetch_one(date_str_q)[0]
                sales_q = "SELECT SUM(quantity) FROM purchases WHERE shop_id = ? AND date(purchase_timestamp) = ?"
                sales_val = self.fetch_one(sales_q, (shop_id, date_val))[0]
            else:
                date_str_q = "SELECT CURDATE() - INTERVAL %d DAY" % i
                date_val = self.fetch_one(date_str_q)[0]
                date_val = date_val.strftime("%Y-%m-%d") if date_val else ""
                sales_q = "SELECT SUM(quantity) FROM purchases WHERE shop_id = %s AND DATE(purchase_timestamp) = %s"
                sales_val = self.fetch_one(sales_q, (shop_id, date_val))[0]
                
            dt_obj = datetime.datetime.strptime(date_val, "%Y-%m-%d")
            day_name = dt_obj.strftime("%a") # e.g. Mon, Tue
            
            days.append(day_name)
            sales.append(int(sales_val) if sales_val is not None else 0)
            
        return {"labels": days, "data": sales}

    def get_monthly_sales_report(self, shop_id):
        # Returns sales volume for each of the last 4 weeks
        weeks = ["Week 4 Ago", "Week 3 Ago", "Week 2 Ago", "This Week"]
        sales = []
        
        for i in range(3, -1, -1):
            start_day = i * 7 + 7
            end_day = i * 7
            if self.use_sqlite:
                sales_q = """
                    SELECT SUM(quantity) FROM purchases 
                    WHERE shop_id = ? 
                    AND purchase_timestamp >= datetime('now', '-%d days')
                    AND purchase_timestamp < datetime('now', '-%d days')
                """ % (start_day, end_day) if i > 0 else """
                    SELECT SUM(quantity) FROM purchases 
                    WHERE shop_id = ? 
                    AND purchase_timestamp >= datetime('now', '-7 days')
                """
                sales_val = self.fetch_one(sales_q, (shop_id,))[0]
            else:
                sales_q = """
                    SELECT SUM(quantity) FROM purchases 
                    WHERE shop_id = %s 
                    AND purchase_timestamp >= NOW() - INTERVAL %d DAY
                    AND purchase_timestamp < NOW() - INTERVAL %d DAY
                """ % (shop_id, start_day, end_day) if i > 0 else """
                    SELECT SUM(quantity) FROM purchases 
                    WHERE shop_id = %s 
                    AND purchase_timestamp >= NOW() - INTERVAL 7 DAY
                """
                sales_val = self.fetch_one(sales_q, (shop_id,))[0]
                
            sales.append(int(sales_val) if sales_val is not None else 0)
            
        return {"labels": weeks, "data": sales}
