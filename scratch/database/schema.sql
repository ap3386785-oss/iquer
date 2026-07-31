-- AI-Based Smart Alcohol Purchase Verification and Limit Monitoring System
-- Database Schema for MySQL

CREATE DATABASE IF NOT EXISTS smart_alcohol_system;
USE smart_alcohol_system;

-- 1. Shops Table
CREATE TABLE IF NOT EXISTS shops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate default shops for testing the multi-shop risk alert feature
INSERT INTO shops (name, location) VALUES 
('Main Street Wines', 'Block 1, Downtown'),
('Highway Plaza Liquors', 'Mile 4, North Expressway'),
('Metro Station Spirits', 'Underground Mall, Central');

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    id_number VARCHAR(50) NOT NULL UNIQUE,
    id_type VARCHAR(50) NOT NULL, -- 'Aadhaar Card' or 'Driving Licence'
    dob DATE NOT NULL,
    photo_path VARCHAR(255) NOT NULL, -- Local path or URL to stored photo
    id_photo_path VARCHAR(255) NULL, -- Local path to stored Aadhaar/DL document photo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Purchases Table
CREATE TABLE IF NOT EXISTS purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    shop_id INT NOT NULL,
    quantity INT NOT NULL, -- Quantity in ml
    remaining_weekly INT NOT NULL, -- Remaining weekly limit in ml
    remaining_monthly INT NOT NULL, -- Remaining monthly limit in ml
    purchase_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
);

-- 4. AI Risk Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NULL, -- Can be NULL if face recognition fails repeatedly and ID is unknown
    shop_id INT NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'multiple_purchases_today', 'multi_shop_purchase', 'repeated_face_failures'
    description TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
);

-- 5. Face Verification Failures Log Table (to detect repeated failures)
CREATE TABLE IF NOT EXISTS face_failures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NULL,
    shop_id INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
);
