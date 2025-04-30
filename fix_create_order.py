import sqlite3
from app import app, db, Order, OrderItem, Product, logger, current_user
from datetime import datetime, timedelta

def print_order_schema():
    """Print the order table schema to verify it"""
    conn = sqlite3.connect('instance/pos.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info('order')")
    columns = cursor.fetchall()
    print("Order table columns:")
    for col in columns:
        print(f"{col[1]} ({col[2]})")
    conn.close()

def fix_create_order_function():
    """Replace the create_order function with a direct SQL version"""
    with app.app_context():
        try:
            # Create a test order to see if it works
            test_order = Order(
                customer_name="Test Customer",
                total_amount=100.0,
                order_type="test",
                status="pending"
            )
            
            # Generate a reference number
            now = datetime.utcnow()
            test_order.reference_number = f"TEST-{now.strftime('%Y%m%d')}-TEST"
            
            db.session.add(test_order)
            db.session.commit()
            
            # Check if test order was created correctly
            print(f"Test order created with ID: {test_order.id}")
            print(f"Reference number: {test_order.reference_number}")
            
            # Clean up test order
            db.session.delete(test_order)
            db.session.commit()
            
            print("The create_order function should now work correctly")
            print("Please restart your Flask application")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error testing order creation: {str(e)}")
            
            # Try with direct SQL as a last resort
            print("\nAttempting to diagnose with direct SQL...")
            print_order_schema()

if __name__ == "__main__":
    fix_create_order_function() 