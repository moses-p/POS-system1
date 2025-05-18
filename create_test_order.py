import sqlite3
from datetime import datetime

# Set these to match a real staff user in your database
STAFF_ID = 2  # Change this to a valid staff user ID

conn = sqlite3.connect('C:/Users/Genius/Documents/POS-system1/instance/pos.db')
cursor = conn.cursor()

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Insert a test order
cursor.execute("""
INSERT INTO 'order' (
    reference_number, customer_id, order_date, total_amount, status,
    customer_name, customer_phone, customer_email, customer_address,
    order_type, created_by_id, updated_at, viewed, viewed_at,
    payment_status, payment_method
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    f'TEST-{now}', None, now, 1000, 'pending',
    'Test Customer', '0700000000', 'test@example.com', 'Test Address',
    'in-store', STAFF_ID, now, 0, None, 'pending', 'cash'
))
order_id = cursor.lastrowid

# Insert a test order item (assumes product with ID 1 exists)
cursor.execute("""
INSERT INTO order_item (order_id, product_id, quantity, price)
VALUES (?, ?, ?, ?)
""", (order_id, 1, 1, 1000))

conn.commit()
print(f"Inserted test order with ID {order_id}")
conn.close() 