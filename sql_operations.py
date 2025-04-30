import sqlite3
import logging
from datetime import datetime
import uuid
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("sql_operations.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a database connection with row factory enabled"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row  # Make rows accessible by column name
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None

def direct_create_order(customer_data, items_data, order_type):
    """
    Create an order directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
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
        INSERT INTO "order" (
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
        
        logger.info(f"Order created successfully with ID: {order_id} and reference: {reference_number}")
        return order_id, reference_number
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return None, f"Error creating order: {str(e)}"

def direct_get_order(order_id):
    """
    Get an order directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        # Get the order
        cursor.execute("""
        SELECT * FROM "order" WHERE id = ?
        """, (order_id,))
        
        order_data = cursor.fetchone()
        
        if not order_data:
            conn.close()
            return None, f"Order {order_id} not found"
        
        # Get the order items - using LEFT JOIN so items will be returned even if products are missing
        cursor.execute("""
        SELECT oi.*, p.name as product_name 
        FROM order_item oi
        LEFT JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """, (order_id,))
        
        items = cursor.fetchall()
        
        # Convert to dictionaries for easier handling
        order = dict(order_data)
        order_items = [dict(item) for item in items]
        
        conn.close()
        
        # If no items were found, don't fail - just return an empty items list
        if not order_items:
            logger.warning(f"No items found for order {order_id}")
            
        return {
            'order': order,
            'items': order_items
        }, None
        
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return None, f"Error getting order: {str(e)}"

def direct_get_products(category=None, limit=100, offset=0):
    """
    Get products directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        query = "SELECT * FROM product"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
            
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return products, None
        
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return None, f"Error getting products: {str(e)}"

def direct_create_user(username, email, password_hash, is_admin=False, is_staff=False):
    """
    Create a user directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM user WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return None, "Username already exists"
            
        # Check if email already exists
        cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return None, "Email already exists"
        
        # Insert the new user
        cursor.execute("""
        INSERT INTO user (username, email, password_hash, is_admin, is_staff)
        VALUES (?, ?, ?, ?, ?)
        """, (username, email, password_hash, is_admin, is_staff))
        
        user_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return user_id, None
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return None, f"Error creating user: {str(e)}"

def direct_get_user(user_id=None, username=None, email=None):
    """
    Get a user directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
        elif username:
            cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        elif email:
            cursor.execute("SELECT * FROM user WHERE email = ?", (email,))
        else:
            conn.close()
            return None, "No search criteria provided"
            
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None, "User not found"
            
        conn.close()
        return dict(user), None
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return None, f"Error getting user: {str(e)}"

def direct_create_product(product_data):
    """
    Create a product directly using SQL
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        # Check if barcode already exists (if provided)
        barcode = product_data.get('barcode')
        if barcode:
            cursor.execute("SELECT id FROM product WHERE barcode = ?", (barcode,))
            if cursor.fetchone():
                conn.close()
                return None, "Barcode already exists"
        
        # Insert the product
        cursor.execute("""
        INSERT INTO product (
            name, description, price, currency, stock, max_stock, 
            reorder_point, unit, category, image_url, barcode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_data.get('name', ''),
            product_data.get('description', ''),
            product_data.get('price', 0),
            product_data.get('currency', 'UGX'),
            product_data.get('stock', 0),
            product_data.get('max_stock', 0),
            product_data.get('reorder_point', 0),
            product_data.get('unit', 'pcs'),
            product_data.get('category', ''),
            product_data.get('image_url', ''),
            barcode
        ))
        
        product_id = cursor.lastrowid
        
        # Record stock movement if initial stock is provided
        stock = product_data.get('stock', 0)
        if stock > 0:
            cursor.execute("""
            INSERT INTO stock_movement (product_id, quantity, movement_type, remaining_stock, notes)
            VALUES (?, ?, ?, ?, ?)
            """, (
                product_id, 
                stock, 
                'restock', 
                stock, 
                f"Initial stock for {product_data.get('name', '')}"
            ))
        
        conn.commit()
        conn.close()
        
        return product_id, None
        
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return None, f"Error creating product: {str(e)}"

def direct_cart_operations(operation, data=None):
    """
    Perform cart operations directly using SQL
    
    Operations:
    - get_cart: Get a cart by ID or user ID
    - add_item: Add an item to a cart
    - update_item: Update a cart item
    - remove_item: Remove an item from a cart
    - clear_cart: Clear all items from a cart
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None, "Database connection failed"
            
        cursor = conn.cursor()
        
        if operation == 'get_cart':
            cart_id = data.get('cart_id')
            user_id = data.get('user_id')
            
            if cart_id:
                cursor.execute("SELECT * FROM cart WHERE id = ?", (cart_id,))
            elif user_id:
                cursor.execute("SELECT * FROM cart WHERE user_id = ? AND status = 'active'", (user_id,))
            else:
                conn.close()
                return None, "No cart ID or user ID provided"
                
            cart = cursor.fetchone()
            
            if not cart:
                # Create a new cart if user_id is provided
                if user_id:
                    cursor.execute("INSERT INTO cart (user_id, status) VALUES (?, 'active')", (user_id,))
                    cart_id = cursor.lastrowid
                    conn.commit()
                    cursor.execute("SELECT * FROM cart WHERE id = ?", (cart_id,))
                    cart = cursor.fetchone()
                else:
                    conn.close()
                    return None, "Cart not found"
            
            # Get cart items
            cursor.execute("""
            SELECT ci.*, p.name as product_name, p.price, p.stock 
            FROM cart_item ci
            JOIN product p ON ci.product_id = p.id
            WHERE ci.cart_id = ?
            """, (cart['id'],))
            
            items = cursor.fetchall()
            
            result = {
                'cart': dict(cart),
                'items': [dict(item) for item in items]
            }
            
            conn.close()
            return result, None
            
        elif operation == 'add_item':
            cart_id = data.get('cart_id')
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            
            if not cart_id or not product_id:
                conn.close()
                return None, "Cart ID and product ID are required"
                
            # Check if item already exists in cart
            cursor.execute("""
            SELECT id, quantity FROM cart_item 
            WHERE cart_id = ? AND product_id = ?
            """, (cart_id, product_id))
            
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update quantity
                new_quantity = existing_item['quantity'] + quantity
                cursor.execute("""
                UPDATE cart_item SET quantity = ? WHERE id = ?
                """, (new_quantity, existing_item['id']))
            else:
                # Add new item
                cursor.execute("""
                INSERT INTO cart_item (cart_id, product_id, quantity)
                VALUES (?, ?, ?)
                """, (cart_id, product_id, quantity))
            
            conn.commit()
            conn.close()
            return True, None
            
        elif operation == 'update_item':
            item_id = data.get('item_id')
            quantity = data.get('quantity')
            
            if not item_id or quantity is None:
                conn.close()
                return None, "Item ID and quantity are required"
                
            if quantity <= 0:
                # Remove the item if quantity is 0 or negative
                cursor.execute("DELETE FROM cart_item WHERE id = ?", (item_id,))
            else:
                # Update quantity
                cursor.execute("UPDATE cart_item SET quantity = ? WHERE id = ?", (quantity, item_id))
                
            conn.commit()
            conn.close()
            return True, None
            
        elif operation == 'remove_item':
            item_id = data.get('item_id')
            
            if not item_id:
                conn.close()
                return None, "Item ID is required"
                
            cursor.execute("DELETE FROM cart_item WHERE id = ?", (item_id,))
            
            conn.commit()
            conn.close()
            return True, None
            
        elif operation == 'clear_cart':
            cart_id = data.get('cart_id')
            
            if not cart_id:
                conn.close()
                return None, "Cart ID is required"
                
            cursor.execute("DELETE FROM cart_item WHERE cart_id = ?", (cart_id,))
            
            conn.commit()
            conn.close()
            return True, None
            
        else:
            conn.close()
            return None, f"Unknown operation: {operation}"
        
    except Exception as e:
        logger.error(f"Error in cart operation {operation}: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return None, f"Error in cart operation: {str(e)}"

# Simple tests for the utility functions
if __name__ == "__main__":
    # Test order creation
    print("Testing direct order creation...")
    customer_data = {
        'customer_name': 'Test Customer',
        'customer_phone': '1234567890',
        'customer_email': 'test@example.com',
        'customer_address': 'Test Address'
    }
    
    items_data = [
        {'product_id': 1, 'quantity': 2, 'price': 10.0}
    ]
    
    order_id, reference = direct_create_order(customer_data, items_data, 'test')
    
    if order_id:
        print(f"Order created successfully: ID={order_id}, Reference={reference}")
        
        # Test getting the order
        print("\nTesting direct order retrieval...")
        order_data, error = direct_get_order(order_id)
        
        if order_data:
            print(f"Order retrieved: {order_data['order']['reference_number']}")
            print(f"Items: {len(order_data['items'])}")
        else:
            print(f"Error: {error}")
    else:
        print(f"Error creating order: {reference}")
        
    print("\nAll tests completed.") 