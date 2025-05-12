-- Users Table (Example - can be expanded)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Store hashed passwords, not plain text!
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    file_name VARCHAR(255) NOT NULL,
    original_file_path VARCHAR(512),
    status VARCHAR(50) DEFAULT 'uploaded',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    raw_text MEDIUMTEXT NULL,
    vendor_name VARCHAR(255) NULL,
    invoice_number VARCHAR(255) NULL,
    invoice_date DATE NULL,
    total_amount DECIMAL(15, 2) NULL, -- Increased precision for amount
    currency VARCHAR(10) NULL, -- To store currency code like 'INR', 'USD' or symbol '₹', '$'
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL -- Or ON DELETE CASCADE if invoices should be deleted with user
);

-- Extracted Invoice Fields Table
CREATE TABLE IF NOT EXISTS invoice_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    field_name VARCHAR(255) NOT NULL, -- e.g., 'Subtotal', 'Tax', 'ItemDescription', 'line_item_1_description'
    field_value TEXT NULL,            -- Ensuring this can be NULL
    confidence FLOAT NULL,            -- OCR confidence for this specific field, if available
    coordinates VARCHAR(255) NULL,    -- Bounding box coordinates of the field on the image (e.g., JSON string)
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoice_fields_invoice_id ON invoice_fields(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_fields_field_name ON invoice_fields(field_name); 