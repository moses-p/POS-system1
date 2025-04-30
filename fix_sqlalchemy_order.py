import sqlite3
import logging
import os
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("sqlalchemy_fix.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_app_py():
    """Create a backup of app.py"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source = 'app.py'
    target = f'app_backup_{timestamp}.py'
    
    if os.path.exists(source):
        shutil.copy2(source, target)
        logger.info(f"App.py backed up to {target}")
        return True
    else:
        logger.warning("App.py not found, no backup created")
        return False

def fix_sqlalchemy_order_issues():
    """Create a patched version of the order retrieval and creation code"""
    # Backup the app first
    backup_app_py()
    
    # Define our replacement functions
    get_order_by_id_replacement = """def get_order_by_id(order_id):
    \"\"\"
    Get an order by ID using direct SQL to bypass SQLAlchemy issues with the 'order' table name
    \"\"\"
    try:
        # Skip SQLAlchemy entirely and use direct SQL
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the order
        cursor.execute(\"\"\"
        SELECT * FROM [order] WHERE id = ?
        \"\"\", (order_id,))
        
        order_row = cursor.fetchone()
        if not order_row:
            conn.close()
            logger.error(f"Order {order_id} not found in database")
            return None
            
        order_dict = dict(order_row)
        
        # Get the order items with LEFT JOIN to products
        cursor.execute(\"\"\"
        SELECT oi.*, p.name as product_name, p.price as product_price 
        FROM order_item oi
        LEFT JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        \"\"\", (order_id,))
        
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Create a SimpleOrder object to mimic the SQLAlchemy Order
        class SimpleOrder:
            def __init__(self, order_data, item_data):
                # Basic order properties
                self.id = order_data.get('id')
                self.reference_number = order_data.get('reference_number', '')
                self.customer_name = order_data.get('customer_name', '')
                self.customer_phone = order_data.get('customer_phone', '')
                self.customer_email = order_data.get('customer_email', '')
                self.customer_address = order_data.get('customer_address', '')
                self.order_date = order_data.get('order_date', '')
                self.total_amount = order_data.get('total_amount', 0)
                self.status = order_data.get('status', 'pending')
                self.order_type = order_data.get('order_type', 'online')
                self.viewed = order_data.get('viewed', 0)
                self.viewed_at = order_data.get('viewed_at')
                self.completed_at = order_data.get('completed_at')
                self.updated_at = order_data.get('updated_at')
                self.created_by_id = order_data.get('created_by_id')
                self.customer_id = order_data.get('customer_id')
                
                # Store item data for items property
                self._items = item_data
            
            @property
            def items(self):
                class SimpleOrderItem:
                    def __init__(self, item_data):
                        self.id = item_data.get('id', 0)
                        self.order_id = item_data.get('order_id', 0)
                        self.product_id = item_data.get('product_id', 0)
                        self.quantity = item_data.get('quantity', 0)
                        self.price = item_data.get('price', 0)
                        self._product_name = item_data.get('product_name', 'Product')
                        self._product_price = item_data.get('product_price', self.price)
                        
                    @property
                    def subtotal(self):
                        return self.price * self.quantity
                        
                    @property
                    def product(self):
                        class SimpleProduct:
                            def __init__(self, name, price):
                                self.name = name
                                self.price = price
                        return SimpleProduct(self._product_name, self._product_price)
                
                return [SimpleOrderItem(item) for item in self._items]
        
        return SimpleOrder(order_dict, items)
        
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        # Make sure to add detailed error info to help debugging
        import traceback
        logger.error(traceback.format_exc())
        return None
"""

    create_order_replacement = """def create_order(customer_data, items_data, order_type):
    \"\"\"
    Centralized function to create orders, using only direct SQL to avoid SQLAlchemy issues
    \"\"\"
    try:
        # Skip SQLAlchemy entirely and use direct SQL
        try:
            # Calculate total amount
            total_amount = sum(item['price'] * item['quantity'] for item in items_data)
            
            # Generate a unique reference number
            now = datetime.utcnow()
            date_part = now.strftime('%Y%m%d')
            random_part = str(uuid.uuid4())[:8]
            reference_number = f"ORD-{date_part}-{random_part}"
            
            # Connect to database
            conn = sqlite3.connect('instance/pos.db')
            cursor = conn.cursor()
            
            # Insert the order
            cursor.execute(\"\"\"
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
                viewed,
                customer_id,
                created_by_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \"\"\", (
                reference_number,
                customer_data.get('customer_name', ''),
                customer_data.get('customer_phone', ''),
                customer_data.get('customer_email', ''),
                customer_data.get('customer_address', ''),
                now.strftime('%Y-%m-%d %H:%M:%S'),
                total_amount,
                'pending',
                order_type,
                0,
                customer_data.get('customer_id'),
                customer_data.get('created_by_id')
            ))
            
            # Get the new order ID
            order_id = cursor.lastrowid
            
            # Insert order items
            for item_data in items_data:
                cursor.execute(\"\"\"
                INSERT INTO order_item (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                \"\"\", (
                    order_id,
                    item_data['product_id'],
                    item_data['quantity'],
                    item_data['price']
                ))
                
                # Update product stock
                cursor.execute(\"\"\"
                UPDATE product SET stock = stock - ? WHERE id = ?
                \"\"\", (item_data['quantity'], item_data['product_id']))
            
            # Commit the transaction
            conn.commit()
            conn.close()
            
            # Return the created order
            order = get_order_by_id(order_id)
            if order:
                logger.info(f"Successfully created order {order_id} with direct SQL")
                return order, None
            else:
                logger.warning(f"Created order {order_id} with direct SQL but can't retrieve it")
                return None, f"Order created with ID {order_id}, but couldn't be retrieved. Try refreshing."
                
        except Exception as e:
            logger.error(f"Error creating order with direct SQL: {str(e)}")
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
            return None, f"Error creating order: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error in create_order: {str(e)}")
        return None, f"Error creating order: {str(e)}"
"""

    # Read the app.py file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the get_order_by_id function
    import re
    
    # Replace get_order_by_id
    get_order_pattern = r'def get_order_by_id\(order_id\):(?:.*?)(?=\ndef |$)'
    if re.search(get_order_pattern, content, re.DOTALL):
        content = re.sub(get_order_pattern, get_order_by_id_replacement, content, flags=re.DOTALL)
        logger.info("Replaced get_order_by_id function")
    else:
        # If function not found, append it at the end
        content += "\n\n" + get_order_by_id_replacement
        logger.info("Added get_order_by_id function at the end of the file")
    
    # Replace create_order
    create_order_pattern = r'def create_order\(customer_data, items_data, order_type\):(?:.*?)(?=\ndef |$)'
    if re.search(create_order_pattern, content, re.DOTALL):
        content = re.sub(create_order_pattern, create_order_replacement, content, flags=re.DOTALL)
        logger.info("Replaced create_order function")
    else:
        # If function not found, append it at the end
        content += "\n\n" + create_order_replacement
        logger.info("Added create_order function at the end of the file")
    
    # Write the modified content back to app.py
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Successfully patched app.py to fix SQLAlchemy order table issues")
    return True

if __name__ == "__main__":
    print("Fixing SQLAlchemy issues with the 'order' table...")
    if fix_sqlalchemy_order_issues():
        print("✅ Fix applied successfully! The app should now be able to create and retrieve orders correctly.")
    else:
        print("❌ Fix failed. Check the logs for more details.") 