CREATE DATABASE IF NOT EXISTS chatbot_analytics;
USE chatbot_analytics;

CREATE TABLE IF NOT EXISTS products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    launch_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    region VARCHAR(80) NOT NULL,
    quantity INT NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    sale_date DATE NOT NULL,
    sales_rep VARCHAR(120),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(120) NOT NULL,
    department VARCHAR(80) NOT NULL,
    job_title VARCHAR(120) NOT NULL,
    join_date DATE NOT NULL,
    employment_status VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    hours_worked DECIMAL(4, 2) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(120) NOT NULL,
    diagnosis VARCHAR(180) NOT NULL,
    attending_doctor VARCHAR(120) NOT NULL,
    visit_date DATE NOT NULL,
    bill_amount DECIMAL(12, 2) NOT NULL
);

INSERT INTO products (product_name, category, unit_price, launch_date, is_active) VALUES
('Apex CRM Suite', 'Software', 499.00, '2025-10-12', TRUE),
('Nova Analytics', 'Software', 799.00, '2025-07-01', TRUE),
('Pulse Tablet', 'Hardware', 299.00, '2024-11-18', TRUE),
('CareSense Monitor', 'Healthcare', 599.00, '2025-01-20', TRUE)
ON DUPLICATE KEY UPDATE product_name = VALUES(product_name);

INSERT INTO sales (product_id, region, quantity, total_amount, sale_date, sales_rep) VALUES
(1, 'North', 12, 5988.00, '2026-05-01', 'Anika Sharma'),
(2, 'West', 8, 6392.00, '2026-05-02', 'Rohit Patel'),
(3, 'South', 16, 4784.00, '2026-05-03', 'Neha Iyer'),
(1, 'East', 10, 4990.00, '2026-05-04', 'Anika Sharma'),
(4, 'North', 5, 2995.00, '2026-05-05', 'Rahul Menon'),
(2, 'South', 6, 4794.00, '2026-04-21', 'Rohit Patel'),
(4, 'West', 3, 1797.00, '2026-04-29', 'Rahul Menon');

INSERT INTO employees (full_name, department, job_title, join_date, employment_status) VALUES
('Mira Kapoor', 'Operations', 'Operations Manager', '2022-03-14', 'Active'),
('Sanjay Verma', 'Sales', 'Senior Sales Executive', '2021-09-10', 'Active'),
('Pooja Nair', 'HR', 'HR Specialist', '2023-06-18', 'Active'),
('Vikram Joshi', 'Engineering', 'Data Engineer', '2024-01-08', 'Active');

INSERT INTO attendance (employee_id, attendance_date, status, hours_worked) VALUES
(1, '2026-05-01', 'Present', 8.0),
(2, '2026-05-01', 'Present', 8.5),
(3, '2026-05-01', 'Leave', 0.0),
(4, '2026-05-01', 'Present', 7.5),
(1, '2026-05-02', 'Present', 8.0),
(2, '2026-05-02', 'Remote', 8.0),
(3, '2026-05-02', 'Present', 8.0),
(4, '2026-05-02', 'Present', 8.0);

INSERT INTO patients (full_name, diagnosis, attending_doctor, visit_date, bill_amount) VALUES
('Aditi Rao', 'Hypertension', 'Dr. Sameer Kulkarni', '2026-05-01', 4500.00),
('Karan Malhotra', 'Diabetes Follow-up', 'Dr. Meera Singh', '2026-05-02', 3200.00),
('Suhani Das', 'Routine Checkup', 'Dr. Meera Singh', '2026-05-03', 1800.00),
('Ritesh Gupta', 'Cardiac Screening', 'Dr. Sameer Kulkarni', '2026-05-04', 6200.00);

