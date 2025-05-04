import sqlite3
import os

def check_database():
    print("Checking database contents...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:", tables)
        
        # Check product table if it exists
        if ('product',) in tables:
            cursor.execute("PRAGMA table_info(product)")
            columns = cursor.fetchall()
            print("\nProduct table columns:", columns)
            
            # Check for data
            cursor.execute("SELECT COUNT(*) FROM product")
            count = cursor.fetchone()[0]
            print(f"\nNumber of products: {count}")
            
            if count > 0:
                cursor.execute("SELECT * FROM product LIMIT 1")
                sample = cursor.fetchone()
                print("\nSample product:", sample)
        
        # Check Order table structure
        print("\nOrder Table Structure:")
        cursor.execute("PRAGMA table_info('order')")
        columns = cursor.fetchall()
        for column in columns:
            print(f"Column: {column[1]}, Type: {column[2]}")
        
        # Check Stock Movements
        print("\nRecent Stock Movements:")
        cursor.execute("""
            SELECT sm.id, sm.product_id, p.name, sm.quantity, sm.movement_type, sm.remaining_stock, sm.timestamp
            FROM stock_movement sm
            JOIN product p ON sm.product_id = p.id
            ORDER BY sm.timestamp DESC 
            LIMIT 10
        """)
        movements = cursor.fetchall()
        for movement in movements:
            print(f"ID: {movement[0]}, Product: {movement[2]} (ID: {movement[1]}), Quantity: {movement[3]}, Type: {movement[4]}, Remaining: {movement[5]}, Time: {movement[6]}")
        
        # Check Order count
        cursor.execute('SELECT COUNT(*) FROM "order"')
        order_count = cursor.fetchone()[0]
        print(f'Order count: {order_count}')
        
        # Check Product count
        cursor.execute('SELECT COUNT(*) FROM product')
        product_count = cursor.fetchone()[0]
        print(f'Product count: {product_count}')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database() 