import sqlite3
import datetime

# Connect to the database
conn = sqlite3.connect('instance/pos.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check product stock
print("=== Current Product Stock ===")
cursor.execute("SELECT id, name, stock, updated_at FROM product ORDER BY id")
products = cursor.fetchall()
for product in products:
    print(f"ID: {product['id']}, Name: {product['name']}, Stock: {product['stock']}, Last Updated: {product['updated_at']}")

print("\n=== Recent Stock Movements ===")
cursor.execute("""
SELECT sm.id, sm.product_id, p.name, sm.quantity, sm.movement_type, sm.remaining_stock, sm.timestamp, sm.notes 
FROM stock_movement sm 
JOIN product p ON sm.product_id = p.id 
ORDER BY sm.timestamp DESC LIMIT 10
""")
movements = cursor.fetchall()
for movement in movements:
    print(f"Movement ID: {movement['id']}, Product: {movement['name']} ({movement['product_id']})")
    print(f"  Quantity: {movement['quantity']}, Type: {movement['movement_type']}, Remaining: {movement['remaining_stock']}")
    print(f"  Time: {movement['timestamp']}, Notes: {movement['notes']}")

print("\n=== Recent Orders ===")
cursor.execute("""
SELECT id, order_date, total_amount, status FROM "order" ORDER BY order_date DESC LIMIT 5
""")
orders = cursor.fetchall()
for order in orders:
    print(f"Order ID: {order['id']}, Date: {order['order_date']}, Amount: {order['total_amount']}, Status: {order['status']}")
    
    # Get order items
    cursor.execute("""
    SELECT oi.id, oi.product_id, p.name, oi.quantity, oi.price 
    FROM order_item oi
    JOIN product p ON oi.product_id = p.id
    WHERE oi.order_id = ?
    """, (order['id'],))
    items = cursor.fetchall()
    for item in items:
        print(f"  Item: {item['name']}, Quantity: {item['quantity']}, Price: {item['price']}")

conn.close() 