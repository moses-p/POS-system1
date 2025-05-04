import sqlite3
import os
from datetime import datetime

def check_orders():
    print("Checking recent orders...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Check recent orders
        print("\nRecent Orders:")
        cursor.execute("""
            SELECT id, reference_number, customer_id, 
                   order_date, total_amount, status, 
                   order_type, created_by_id
            FROM "order"
            ORDER BY order_date DESC 
            LIMIT 10
        """)
        orders = cursor.fetchall()
        
        if not orders:
            print("No orders found in database.")
        
        for order in orders:
            order_date = datetime.fromisoformat(order['order_date']) if order['order_date'] else None
            formatted_date = order_date.strftime('%Y-%m-%d %H:%M:%S') if order_date else 'None'
            
            print(f"Order ID: {order['id']}")
            print(f"  Reference: {order['reference_number']}")
            print(f"  Date: {formatted_date}")
            print(f"  Amount: {order['total_amount']}")
            print(f"  Status: {order['status']}")
            print(f"  Type: {order['order_type']}")
            
            # Get order items
            cursor.execute("""
                SELECT oi.id, oi.product_id, p.name, oi.quantity, oi.price
                FROM order_item oi
                JOIN product p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            """, (order['id'],))
            items = cursor.fetchall()
            
            print("  Items:")
            for item in items:
                print(f"    - {item['quantity']}x {item['name']} @ {item['price']} = {item['quantity'] * item['price']}")
            
            print("-" * 40)
        
        # Get total sales per day for the last 7 days
        print("\nDaily Sales (Last 7 days):")
        cursor.execute("""
            SELECT date(order_date) as sale_date, 
                   SUM(total_amount) as daily_total,
                   COUNT(*) as order_count
            FROM "order"
            GROUP BY date(order_date)
            ORDER BY sale_date DESC
            LIMIT 7
        """)
        daily_sales = cursor.fetchall()
        
        if not daily_sales:
            print("No daily sales data found.")
        
        for day in daily_sales:
            print(f"Date: {day['sale_date']}, Total: {day['daily_total']}, Orders: {day['order_count']}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking orders: {str(e)}")

if __name__ == "__main__":
    check_orders() 