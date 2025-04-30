import re
import logging
import os
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("order_retrieval_fix.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_app_py():
    """Create a backup of app.py"""
    try:
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
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def fix_get_order_by_id():
    """Fix the get_order_by_id function in app.py"""
    try:
        # First make a backup
        backup_app_py()
        
        # Read app.py
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Define the new get_order_by_id function
        new_function = '''def get_order_by_id(order_id):
    """
    Get an order by ID with fallback to direct SQL if SQLAlchemy fails
    """
    try:
        # First try with SQLAlchemy
        order = Order.query.get(order_id)
        if order:
            return order
            
        # If not found with SQLAlchemy, try direct SQL
        logger.warning(f"Order {order_id} not found with SQLAlchemy, trying direct SQL")
        
        try:
            # Direct database query - no JOIN with product table
            conn = sqlite3.connect('instance/pos.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get the order
            cursor.execute("""
            SELECT * FROM "order" WHERE id = ?
            """, (order_id,))
            
            order_row = cursor.fetchone()
            if not order_row:
                conn.close()
                logger.error(f"Order {order_id} not found in direct SQL")
                return None
                
            order_dict = dict(order_row)
            
            # Get the order items without joining to products
            cursor.execute("""
            SELECT * FROM order_item WHERE order_id = ?
            """, (order_id,))
            
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
                            self._product_name = None
                            
                            # Try to get product name if we can
                            try:
                                conn = sqlite3.connect('instance/pos.db')
                                conn.row_factory = sqlite3.Row
                                cursor = conn.cursor()
                                cursor.execute("SELECT name FROM product WHERE id = ?", (self.product_id,))
                                product = cursor.fetchone()
                                if product:
                                    self._product_name = product['name']
                                conn.close()
                            except:
                                pass
                            
                        @property
                        def subtotal(self):
                            return self.price * self.quantity
                            
                        @property
                        def product(self):
                            class SimpleProduct:
                                def __init__(self, name, price):
                                    self.name = name
                                    self.price = price
                            return SimpleProduct(self._product_name or "Product", self.price)
                    
                    return [SimpleOrderItem(item) for item in self._items]
            
            return SimpleOrder(order_dict, items)
            
        except Exception as inner_e:
            logger.error(f"Error in direct SQL retrieval: {str(inner_e)}")
            return None
    
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        return None
'''
        
        # Replace existing get_order_by_id function
        pattern = r'def get_order_by_id\(order_id\):(?:.*?)return None\n'
        modified_content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        
        # If the function wasn't replaced, add it at the end
        if modified_content == content:
            logger.warning("Could not find and replace get_order_by_id function, appending it")
            modified_content = content + "\n\n" + new_function
        
        # Write the modified content back to app.py
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(modified_content)
            
        logger.info("Successfully updated get_order_by_id function in app.py")
        return True
        
    except Exception as e:
        logger.error(f"Error updating get_order_by_id: {str(e)}")
        return False

if __name__ == "__main__":
    fix_get_order_by_id() 