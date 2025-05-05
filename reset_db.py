import os
import sqlite3
from datetime import datetime
import shutil

print("Starting database reset process...")

# Path to the database file
db_path = 'instance/pos.db'
backup_path = 'instance/pos.db.bak'

# Create backup of existing database if it exists
if os.path.exists(db_path):
    print(f"Creating backup of existing database to {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("Database backup created.")
    
    # Now remove the existing database
    print(f"Removing existing database: {db_path}")
    os.remove(db_path)
    print("Existing database removed.")

# Create a new database
print("Creating new database...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
print("Creating tables...")

# Create User table
cursor.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    is_admin BOOLEAN,
    is_staff BOOLEAN DEFAULT 0
)
''')

# Create Product table
cursor.execute('''
CREATE TABLE product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price REAL,
    stock REAL,
    max_stock REAL,
    reorder_point REAL,
    unit TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create StockMovement table
cursor.execute('''
CREATE TABLE stock_movement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    quantity REAL,
    movement_type TEXT,
    remaining_stock REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES product (id)
)
''')

# Create Cart table
cursor.execute('''
CREATE TABLE cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE,
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create CartItem table
cursor.execute('''
CREATE TABLE cart_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cart_id) REFERENCES cart (id),
    FOREIGN KEY (product_id) REFERENCES product (id)
)
''')

# Create Order table
cursor.execute('''
CREATE TABLE "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_number TEXT UNIQUE,
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    total_amount REAL,
    status TEXT DEFAULT 'pending',
    payment_status TEXT DEFAULT 'pending',
    order_type TEXT DEFAULT 'online',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
)
''')

# Create OrderItem table
cursor.execute('''
CREATE TABLE order_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES "order" (id),
    FOREIGN KEY (product_id) REFERENCES product (id)
)
''')

# Add an admin user
from werkzeug.security import generate_password_hash
admin_password_hash = generate_password_hash('admin123')

cursor.execute('''
INSERT INTO user (username, email, password_hash, is_admin, is_staff)
VALUES (?, ?, ?, ?, ?)
''', ('admin', 'admin@example.com', admin_password_hash, 1, 1))

# Add a test product
cursor.execute('''
INSERT INTO product (name, description, price, stock, max_stock, reorder_point, unit, category)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', ('Test Product', 'A test product with accurate stock', 10.0, 20.0, 100.0, 5.0, 'pcs', 'Test'))

# Add initial stock movement
cursor.execute('''
INSERT INTO stock_movement (product_id, quantity, movement_type, remaining_stock, notes)
VALUES (?, ?, ?, ?, ?)
''', (1, 20.0, 'restock', 20.0, 'Initial stock'))

# Commit changes
conn.commit()

# Verify that tables were created
print("Verifying database setup...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables created: {[table[0] for table in tables]}")

# Verify that admin user was created
cursor.execute("SELECT id, username, is_admin FROM user")
users = cursor.fetchall()
print(f"Users created: {users}")

# Verify that test product was created
cursor.execute("SELECT id, name, stock FROM product")
products = cursor.fetchall()
print(f"Products created: {products}")

# Close connection
conn.close()

print("Database reset completed successfully!")
print("Please restart the application.") 