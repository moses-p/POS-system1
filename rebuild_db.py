import os
import sqlite3
from datetime import datetime

# Debug print for troubleshooting
print("Starting rebuild_db.py script execution...")

try:
    from app import app, db, User, Product, StockMovement, init_db
    print("Successfully imported required modules from app")
except Exception as e:
    print(f"ERROR: Could not import required modules from app: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

def rebuild_database():
    """
    Completely rebuild the database from scratch:
    1. Delete the existing database file
    2. Create a new database with the correct schema
    3. Initialize it with required data
    """
    print("Starting database rebuild process...")
    
    # Path to the database file
    db_path = 'instance/pos.db'
    
    # Step 1: Delete the existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
        print("Existing database removed.")
    
    # Step 2: Create all tables using SQLAlchemy models
    with app.app_context():
        print("Creating new database tables...")
        db.create_all()
        print("Database tables created successfully.")
        
        # Step 3: Initialize with required data (admin user)
        print("Initializing database with required data...")
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Add a sample product for testing
        product = Product(
            name='Test Product',
            description='A test product for verifying stock updates',
            price=10.0,
            stock=10.0,
            max_stock=100.0,
            reorder_point=5.0,
            unit='pcs',
            category='Test'
        )
        db.session.add(product)
        
        # Record initial stock movement
        movement = StockMovement(
            product_id=1,  # Will be the first product
            quantity=10.0,
            movement_type='restock',
            remaining_stock=10.0,
            notes='Initial stock'
        )
        db.session.add(movement)
        
        # Commit all changes
        db.session.commit()
        print("Database initialized with admin user and sample product.")
        
        # Verify the database integrity
        print("Verifying database integrity...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check User table
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"User count: {user_count}")
        
        # Check Product table
        cursor.execute("SELECT COUNT(*) FROM product")
        product_count = cursor.fetchone()[0]
        print(f"Product count: {product_count}")
        
        # Check StockMovement table
        cursor.execute("SELECT COUNT(*) FROM stock_movement")
        movement_count = cursor.fetchone()[0]
        print(f"Stock movement count: {movement_count}")
        
        # Check stock column definition 
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        for col in columns:
            if col[1] == 'stock':
                print(f"Stock column definition: {col}")
        
        conn.close()
    
    print("Database rebuild completed successfully!")
    print("Please restart the application to use the rebuilt database.")

if __name__ == "__main__":
    try:
        print("Executing rebuild_database() function...")
        rebuild_database()
    except Exception as e:
        print(f"ERROR in rebuild_database(): {str(e)}")
        import traceback
        traceback.print_exc() 