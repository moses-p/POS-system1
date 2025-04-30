import sqlite3
import sys
import logging
from datetime import datetime
import os.path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_direct_order_retrieval(order_id=None):
    """Test retrieving an order directly with SQL"""
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # If no order_id provided, try to find the most recent order
        if not order_id:
            cursor.execute("SELECT id FROM 'order' ORDER BY order_date DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                order_id = result['id']
            else:
                logger.error("No orders found in the database")
                return False
        
        # Get the order
        cursor.execute("SELECT * FROM 'order' WHERE id = ?", (order_id,))
        order_data = cursor.fetchone()
        
        if not order_data:
            logger.error(f"Order {order_id} not found")
            return False
            
        logger.info(f"Found order: ID={order_id}, Reference={order_data['reference_number']}, "
                   f"Customer={order_data['customer_name']}, Amount={order_data['total_amount']}")
        
        # Get the order items with LEFT JOIN
        cursor.execute("""
        SELECT oi.*, p.name as product_name 
        FROM order_item oi
        LEFT JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """, (order_id,))
        
        items = cursor.fetchall()
        
        if not items:
            logger.warning(f"No items found for order {order_id}")
        else:
            logger.info(f"Found {len(items)} items for order {order_id}:")
            for item in items:
                product_name = item['product_name'] if item['product_name'] else "Unknown Product"
                logger.info(f"  - {product_name}: {item['quantity']} x {item['price']} = {item['quantity'] * item['price']}")
        
        # Now import the app and try the app's get_order_by_id function
        try:
            sys.path.append('.')
            from app import get_order_by_id
            
            logger.info("\nTesting app.get_order_by_id function:")
            order = get_order_by_id(order_id)
            
            if not order:
                logger.error(f"get_order_by_id({order_id}) returned None")
                conn.close()
                return False
                
            logger.info(f"Successfully retrieved order: ID={order.id}, Reference={order.reference_number}, "
                       f"Customer={order.customer_name}, Amount={order.total_amount}")
            
            if hasattr(order, 'items'):
                logger.info(f"Order has {len(order.items)} items:")
                for item in order.items:
                    product_name = item.product.name if hasattr(item, 'product') and item.product else "Unknown Product"
                    logger.info(f"  - {product_name}: {item.quantity} x {item.price} = {item.subtotal}")
            else:
                logger.warning("Order has no items property")
                
            logger.info("\nOrder retrieval test PASSED!")
            
        except Exception as e:
            logger.error(f"Error testing get_order_by_id: {str(e)}")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error testing direct order retrieval: {str(e)}")
        return False

def test_create_order():
    """Test creating an order and retrieving it"""
    try:
        # First make sure we have at least one product
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if we have any products
        cursor.execute("SELECT COUNT(*) FROM product")
        product_count = cursor.fetchone()[0]
        
        if product_count == 0:
            # Create a test product
            logger.info("No products found. Creating a test product...")
            cursor.execute("""
            INSERT INTO product (name, description, price, stock, max_stock, unit, category)
            VALUES ('Test Product', 'Created for testing', 100, 100, 200, 'pcs', 'test')
            """)
            conn.commit()
            
            cursor.execute("SELECT id FROM product ORDER BY id DESC LIMIT 1")
            product_id = cursor.fetchone()[0]
            logger.info(f"Created test product with ID {product_id}")
        else:
            # Get the first product ID
            cursor.execute("SELECT id, name, price FROM product LIMIT 1")
            product = cursor.fetchone()
            product_id = product['id']
            logger.info(f"Using existing product: {product['name']} (ID: {product_id}, Price: {product['price']})")
        
        # Import create_order function
        sys.path.append('.')
        try:
            from app import create_order
            
            # Create test customer data
            customer_data = {
                'customer_name': f'Test Customer {datetime.now().strftime("%Y%m%d%H%M%S")}',
                'customer_phone': '1234567890',
                'customer_email': 'test@example.com',
                'customer_address': 'Test Address'
            }
            
            # Create test order items
            items_data = [
                {
                    'product_id': product_id,
                    'quantity': 1,
                    'price': 100
                }
            ]
            
            # Create the order
            logger.info("\nCreating test order...")
            order, error = create_order(customer_data, items_data, 'test')
            
            if error:
                logger.error(f"Error creating order: {error}")
                conn.close()
                return False
                
            if not order:
                logger.error("Order creation failed - no order returned and no error")
                conn.close()
                return False
                
            logger.info(f"Successfully created order: ID={order.id}, Reference={order.reference_number}")
            
            # Now test retrieving the order
            logger.info("\nTesting order retrieval for newly created order...")
            return test_direct_order_retrieval(order.id)
            
        except Exception as e:
            logger.error(f"Error importing/using create_order function: {str(e)}")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"Error in test_create_order: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if the database file exists
    if not os.path.exists('instance/pos.db'):
        logger.error("Database file not found. Please make sure you're running this from the correct directory.")
        sys.exit(1)
    
    print("\n=== Testing Order Retrieval System ===\n")
    
    # Test retrieving the most recent order first
    print("\n--- Testing retrieval of most recent order ---\n")
    if test_direct_order_retrieval():
        print("\n✅ Successfully retrieved existing order")
    else:
        print("\n❌ Failed to retrieve existing order")
    
    # Now test creating a new order and retrieving it
    print("\n--- Testing order creation and retrieval ---\n")
    if test_create_order():
        print("\n✅ Successfully created and retrieved a new order")
    else:
        print("\n❌ Failed to create or retrieve a new order")
    
    print("\n=== Test Complete ===\n") 