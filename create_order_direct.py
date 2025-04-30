import sqlite3
import os
from datetime import datetime
import uuid

def direct_create_order(customer_data, items_data, order_type):
    """
    Create an order directly using SQL instead of SQLAlchemy
    
    Args:
        customer_data: Dictionary containing customer information
        items_data: List of dictionaries containing order items
        order_type: String indicating the type of order ('online', 'in-store', etc.)
        
    Returns:
        tuple: (order_id, reference_number) or (None, error_message)
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Calculate total amount
        total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in items_data)
        
        # Generate a unique reference number
        now = datetime.utcnow()
        date_part = now.strftime('%Y%m%d')
        random_part = str(uuid.uuid4())[:8]
        reference_number = f"ORD-{date_part}-{random_part}"
        
        # Insert order using SQL
        cursor.execute('''
        INSERT INTO [order] (
            reference_number, 
            customer_name, 
            customer_phone, 
            customer_email, 
            customer_address, 
            order_date, 
            total_amount, 
            status, 
            order_type, 
            viewed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reference_number,
            customer_data.get('customer_name', ''),
            customer_data.get('customer_phone', ''),
            customer_data.get('customer_email', ''),
            customer_data.get('customer_address', ''),
            now.strftime('%Y-%m-%d %H:%M:%S'),
            total_amount,
            'pending',
            order_type,
            0
        ))
        
        # Get the ID of the new order
        order_id = cursor.lastrowid
        
        # Insert order items
        for item in items_data:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            
            cursor.execute('''
            INSERT INTO order_item (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
            ''', (order_id, product_id, quantity, price))
            
            # Update product stock
            cursor.execute('''
            UPDATE product SET stock = stock - ? WHERE id = ?
            ''', (quantity, product_id))
        
        # Commit the transaction
        conn.commit()
        conn.close()
        
        print(f"Order created successfully with ID: {order_id} and reference: {reference_number}")
        return order_id, reference_number
        
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return None, f"Error creating order: {str(e)}"

def patch_app():
    """
    Create a demonstration script to show how to modify app.py to use direct SQL
    """
    patch_text = """
# Add this import at the top of app.py
from create_order_direct import direct_create_order

# Then modify the create_order function to use direct SQL when necessary:

def create_order(customer_data, items_data, order_type):
    '''
    Centralized function to create orders from different contexts
    '''
    try:
        # First try using SQLAlchemy
        # ... existing code ...
        
        # If that fails, fall back to direct SQL
    except SQLAlchemyError as e:
        logger.warning(f"SQLAlchemy error when creating order, falling back to direct SQL: {str(e)}")
        order_id, reference_number = direct_create_order(customer_data, items_data, order_type)
        
        if order_id:
            # Get the order using the ID
            order = Order.query.get(order_id)
            return order, None
        else:
            return None, reference_number  # reference_number contains the error message
    """
    print(patch_text)

if __name__ == "__main__":
    # Test the direct SQL order creation
    customer_data = {
        'customer_name': 'Test Customer',
        'customer_phone': '0777777777',
        'customer_email': 'test@example.com',
        'customer_address': 'Test Address'
    }
    
    # You'll need at least one product in the database for this to work
    items_data = [
        {
            'product_id': 1,  # Change this to a valid product ID in your database
            'quantity': 1,
            'price': 100.0
        }
    ]
    
    order_id, reference = direct_create_order(customer_data, items_data, 'test')
    
    if order_id:
        print(f"Success! Created order {order_id} with reference {reference}")
    else:
        print(f"Failed: {reference}")  # reference contains error message on failure 