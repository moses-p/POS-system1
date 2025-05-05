import sqlite3
from datetime import datetime

def add_missing_products():
    print("Adding missing products to the database...")
    
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Check if product ID 2 exists
        cursor.execute("SELECT id FROM product WHERE id = 2")
        product = cursor.fetchone()
        
        if not product:
            print("Adding product with ID 2...")
            
            # Get current timestamp
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            
            # Add product with ID 2
            cursor.execute('''
            INSERT INTO product (id, name, description, price, stock, max_stock, reorder_point, unit, category, created_at, updated_at)
            VALUES (2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('Sample Product', 'A sample product for testing', 15.0, 50.0, 100.0, 10.0, 'units', 'Sample', now, now))
            
            # Add initial stock movement
            cursor.execute('''
            INSERT INTO stock_movement (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (2, 50.0, 'restock', 50.0, now, 'Initial stock'))
            
            print("Product with ID 2 added successfully!")
        else:
            print("Product with ID 2 already exists.")
        
        # Commit changes
        conn.commit()
        print("Database updated successfully!")
        
        # Verify products
        cursor.execute("SELECT id, name, stock FROM product")
        products = cursor.fetchall()
        print("\nCurrent products:")
        for product in products:
            print(f"ID: {product[0]}, Name: {product[1]}, Stock: {product[2]}")
        
        conn.close()
    except Exception as e:
        print(f"Error adding products: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    add_missing_products() 