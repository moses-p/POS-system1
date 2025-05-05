import sqlite3
import os
from datetime import datetime
import uuid
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Log the incoming data
        logger.info(f"Creating order with: customer_data={customer_data}, items_count={len(items_data)}, order_type={order_type}")
        
        # Create transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Get current datetime for consistency
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Get or create customer ID (use null if not provided)
        customer_id = customer_data.get('customer_id')
        
        # Get current user ID for created_by (use null if not provided)
        created_by_id = customer_data.get('created_by_id')
        
        # Log customer and user IDs
        logger.info(f"Using customer_id={customer_id}, created_by_id={created_by_id}")
        
        # Pre-validate all products and stock before attempting any updates
        valid_items = []
        stock_issues = []
        
        for item in items_data:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            
            if not product_id or not quantity:
                stock_issues.append(f"Invalid product data: {item}")
                continue
                
            # Check if product exists and has enough stock
            cursor.execute("SELECT id, name, stock FROM product WHERE id = ?", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                stock_issues.append(f"Product ID {product_id} not found")
                continue
                
            current_stock = product['stock']
            product_name = product['name']
            
            if current_stock < quantity:
                stock_issues.append(f"Insufficient stock for {product_name}: requested {quantity}, available {current_stock}")
                # Don't continue with this item
                continue
                
            # Item is valid, add to valid items list
            item['current_stock'] = current_stock
            item['product_name'] = product_name
            valid_items.append(item)
            
        # If we have stock issues and no valid items, fail early
        if stock_issues and not valid_items:
            logger.error(f"Order creation failed due to stock issues: {stock_issues}")
            return None, f"Order creation failed: {'; '.join(stock_issues)}"
            
        # If we have some stock issues but also valid items, log warning and continue with valid items
        if stock_issues:
            logger.warning(f"Some items will be skipped due to stock issues: {stock_issues}")
            
        # Recalculate total amount based on valid items only
        total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in valid_items)
        
        if total_amount <= 0:
            logger.error("Order has zero or negative total amount")
            return None, "Order has no valid items or zero total amount"
            
        # Generate reference number
        reference_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        
        # Create new order
        cursor.execute("""
            INSERT INTO 'order' (
                reference_number, customer_id, order_date, total_amount, status, 
                customer_name, customer_phone, customer_email, customer_address, 
                order_type, created_by_id, updated_at, viewed, viewed_at,
                payment_status, payment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reference_number,
            customer_id,
            now,
            total_amount,
            'pending',
            customer_data.get('customer_name', ''),
            customer_data.get('customer_phone', ''),
            customer_data.get('customer_email', ''),
            customer_data.get('customer_address', ''),
            order_type,
            created_by_id,
            now,
            0,  # viewed
            None,  # viewed_at
            'pending',  # payment_status
            'cash'  # payment_method
        ))
        
        # Get the order ID
        order_id = cursor.lastrowid
        
        if not order_id:
            logger.error("Failed to get order ID after insertion")
            conn.rollback()
            return None, "Failed to create order"
            
        logger.info(f"Created order with ID {order_id}")
        
        # Add order items and update stock for valid items
        stock_updates = []
        
        for item in valid_items:
            product_id = item['product_id']
            quantity = item['quantity']
            price = item['price']
            current_stock = item['current_stock']
            product_name = item['product_name']
            
            # Insert order item
            cursor.execute("""
                INSERT INTO order_item (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                product_id,
                quantity,
                price
            ))
            
            # Keep track of stock updates for logging
            stock_updates.append({
                'product_id': product_id,
                'product_name': product_name,
                'before': current_stock,
                'quantity': quantity,
                'after': current_stock - quantity
            })
            
            # Calculate new stock level
            new_stock = current_stock - quantity
            
            # Update product stock
            cursor.execute("""
                UPDATE product
                SET stock = ?, updated_at = ?
                WHERE id = ?
            """, (
                new_stock,
                now,
                product_id
            ))
            
            # Add stock movement record
            cursor.execute("""
                INSERT INTO stock_movement (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                quantity,
                'sale',
                new_stock,
                now,
                f"Order #{order_id} ({reference_number})"
            ))
            
            logger.info(f"Updated stock for product {product_id} ({product_name}): -{quantity}, remaining: {new_stock}")
        
        # Commit the transaction
        conn.commit()
        
        # Log all stock updates
        logger.info(f"Order {order_id} created with {len(stock_updates)} stock updates:")
        for update in stock_updates:
            logger.info(f"  - {update['product_name']}: {update['before']} -> {update['after']} (-{update['quantity']})")
        
        # Create a simple object to return
        class SimpleOrder:
            def __init__(self, id, reference_number):
                self.id = id
                self.reference_number = reference_number
                
        return SimpleOrder(order_id, reference_number), None
        
    except sqlite3.Error as sql_error:
        # Handle specific SQLite errors
        error_message = str(sql_error)
        logger.error(f"SQLite error creating order: {error_message}")
        logger.error(traceback.format_exc())
        
        # Try to provide more helpful error messages
        if "no such column" in error_message:
            logger.error("Database schema issue detected: column missing")
            error_message = f"Database schema error: {error_message}. The database may need to be updated."
        elif "FOREIGN KEY constraint failed" in error_message:
            logger.error("Foreign key constraint violation detected")
            error_message = "Order creation failed due to invalid references. Please check customer or product data."
        
        # Attempt rollback
        try:
            if conn and conn.in_transaction:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {str(rollback_error)}")
            
        return None, error_message
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Try to rollback the transaction
        try:
            if conn and conn.in_transaction:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {str(rollback_error)}")
            
        return None, str(e)
        
    finally:
        # Close the connection
        try:
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        except Exception as close_error:
            logger.error(f"Error closing database connection: {str(close_error)}")

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
    
    order, error = direct_create_order(customer_data, items_data, 'test')
    
    if order:
        print(f"Success! Created order {order.id} with reference {order.reference_number}")
    else:
        print(f"Failed: {error}")  # error contains error message on failure 