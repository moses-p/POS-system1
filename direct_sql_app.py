import re
import os
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("app_update.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_app():
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

def update_imports():
    """Add imports for direct SQL operations"""
    try:
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Check if the imports are already present
        if 'from sql_operations import' in content:
            logger.info("SQL operations imports already present")
            return content
            
        # Add imports after SQLAlchemy imports
        pattern = r'(from sqlalchemy\.exc import SQLAlchemyError.*?\n)'
        replacement = r'\1from sql_operations import direct_create_order, direct_get_order, direct_cart_operations, direct_get_products, direct_create_user, direct_get_user, direct_create_product\n'
        
        modified_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if modified_content == content:
            # If the pattern didn't match, add imports at the top after other imports
            logger.warning("Could not find SQLAlchemy imports, adding imports at the top")
            import_block = "from sql_operations import direct_create_order, direct_get_order, direct_cart_operations, direct_get_products, direct_create_user, direct_get_user, direct_create_product\n"
            modified_content = content.replace("# Import required modules\n", "# Import required modules\n" + import_block)
            
        return modified_content
    except Exception as e:
        logger.error(f"Error updating imports: {str(e)}")
        return None

def update_get_order_by_id(content):
    """Update or add the get_order_by_id function"""
    try:
        # Check if the function already exists
        if 'def get_order_by_id(' in content:
            logger.info("get_order_by_id function already exists")
            # We'll update it anyway
            pattern = r'def get_order_by_id\(.*?\):.*?return.*?\n'
            replacement = '''def get_order_by_id(order_id):
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
        order_data, error = direct_get_order(order_id)
        
        if error:
            logger.error(f"Error getting order with direct SQL: {error}")
            return None
            
        if not order_data:
            return None
            
        # Create a simple object with the essential info
        class SimpleOrder:
            def __init__(self, order_dict, items_list):
                self.id = order_dict['id']
                self.reference_number = order_dict.get('reference_number', '')
                self.customer_name = order_dict.get('customer_name', '')
                self.order_date = order_dict.get('order_date', '')
                self.total_amount = order_dict.get('total_amount', 0)
                self.status = order_dict.get('status', 'pending')
                self._items = items_list or []
                
            @property
            def items(self):
                # Convert item dictionaries to SimpleOrderItem objects
                class SimpleOrderItem:
                    def __init__(self, item_dict):
                        self.id = item_dict.get('id', 0)
                        self.order_id = item_dict.get('order_id', 0)
                        self.product_id = item_dict.get('product_id', 0)
                        self.quantity = item_dict.get('quantity', 0)
                        self.price = item_dict.get('price', 0)
                        self.product_name = item_dict.get('product_name', 'Unknown Product')
                        
                    @property
                    def subtotal(self):
                        return self.price * self.quantity
                        
                return [SimpleOrderItem(item) for item in self._items]
        
        # Create a simple representation of the order
        return SimpleOrder(order_data['order'], order_data['items'])
    
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        return None
'''
            
            modified_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            if modified_content == content:
                # If the pattern didn't match, append the function
                logger.warning("Could not find get_order_by_id function, adding it")
                modified_content = content + "\n\n" + replacement
        else:
            # Add the function at the end of the file
            logger.info("Adding get_order_by_id function")
            modified_content = content + "\n\n" + '''def get_order_by_id(order_id):
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
        order_data, error = direct_get_order(order_id)
        
        if error:
            logger.error(f"Error getting order with direct SQL: {error}")
            return None
            
        if not order_data:
            return None
            
        # Create a simple object with the essential info
        class SimpleOrder:
            def __init__(self, order_dict, items_list):
                self.id = order_dict['id']
                self.reference_number = order_dict.get('reference_number', '')
                self.customer_name = order_dict.get('customer_name', '')
                self.order_date = order_dict.get('order_date', '')
                self.total_amount = order_dict.get('total_amount', 0)
                self.status = order_dict.get('status', 'pending')
                self._items = items_list or []
                
            @property
            def items(self):
                # Convert item dictionaries to SimpleOrderItem objects
                class SimpleOrderItem:
                    def __init__(self, item_dict):
                        self.id = item_dict.get('id', 0)
                        self.order_id = item_dict.get('order_id', 0)
                        self.product_id = item_dict.get('product_id', 0)
                        self.quantity = item_dict.get('quantity', 0)
                        self.price = item_dict.get('price', 0)
                        self.product_name = item_dict.get('product_name', 'Unknown Product')
                        
                    @property
                    def subtotal(self):
                        return self.price * self.quantity
                        
                return [SimpleOrderItem(item) for item in self._items]
        
        # Create a simple representation of the order
        return SimpleOrder(order_data['order'], order_data['items'])
    
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        return None
'''
        
        return modified_content
    except Exception as e:
        logger.error(f"Error updating get_order_by_id: {str(e)}")
        return content

def update_create_order_function(content):
    """Update the create_order function to better handle direct SQL fallback"""
    try:
        if 'def create_order(' not in content:
            logger.warning("create_order function not found")
            return content
            
        pattern = r'def create_order\((.*?)\):.*?try:.*?except Exception as e:.*?return None, f"Error creating order: {str\(e\)}"'
        replacement = '''def create_order(customer_data, items_data, order_type):
    """
    Centralized function to create orders from different contexts, with fallback to direct SQL
    """
    try:
        # First try using SQLAlchemy
        try:
            # Create a new order
            order = Order(
                customer_name=customer_data.get('customer_name', ''),
                customer_phone=customer_data.get('customer_phone', ''),
                customer_email=customer_data.get('customer_email', ''),
                customer_address=customer_data.get('customer_address', ''),
                total_amount=sum(item['price'] * item['quantity'] for item in items_data),
                order_type=order_type,
                customer_id=customer_data.get('customer_id'),
                created_by_id=customer_data.get('created_by_id')
            )
            
            # Add the order to the database
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Add order items
            for item_data in items_data:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data['product_id'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                db.session.add(order_item)
                
                # Update product stock
                product = Product.query.get(item_data['product_id'])
                if product:
                    product.update_stock(item_data['quantity'], 'sale')
            
            # Generate reference number
            now = datetime.utcnow()
            order.reference_number = f"ORD-{now.strftime('%Y%m%d')}-{order.id}"
            
            # Commit the transaction
            db.session.commit()
            
            # Return the created order
            return order, None
            
        except SQLAlchemyError as e:
            # If we get a SQLAlchemy error, try the direct SQL approach
            logger.warning(f"SQLAlchemy error when creating order, falling back to direct SQL: {str(e)}")
            db.session.rollback()
            
            # Fall back to direct SQL approach
            order_id, reference = direct_create_order(customer_data, items_data, order_type)
            
            if order_id:
                # Get the order using our resilient function
                order = get_order_by_id(order_id)
                if order:
                    return order, None
                else:
                    # If we can't get the order, return a generic success message
                    logger.warning(f"Created order {order_id} with direct SQL but can't access it")
                    return None, f"Order created with ID {order_id}, but couldn't be retrieved"
            else:
                return None, reference  # reference contains the error message
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating order: {str(e)}")
        return None, f"Error creating order: {str(e)}"
'''
        
        modified_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if modified_content == content:
            logger.warning("Could not update create_order function")
            
        return modified_content
    except Exception as e:
        logger.error(f"Error updating create_order function: {str(e)}")
        return content

def update_order_routes(content):
    """Update specific order-related routes to use get_order_by_id"""
    try:
        # Update print_receipt route
        receipt_pattern = r'@app\.route\(\'/receipt/<int:order_id>\'\)\ndef print_receipt\(order_id\):.*?return render_template\(\'receipt\.html\', order=order, tax_rate=tax_rate, current_user=current_user\)'
        receipt_replacement = '''@app.route('/receipt/<int:order_id>')
def print_receipt(order_id):
    try:
        # Use our resilient get_order_by_id function
        order = get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Add tax rate for receipt calculations
        tax_rate = 0.18  # 18% VAT
        # Pass current_user to template even for anonymous users
        return render_template('receipt.html', order=order, tax_rate=tax_rate, current_user=current_user)
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index'))'''
        
        modified_content = re.sub(receipt_pattern, receipt_replacement, content, flags=re.DOTALL)
        
        # Update order_confirmation route
        confirmation_pattern = r'@app\.route\(\'/order/<int:order_id>\'\)\n@login_required\ndef order_confirmation\(order_id\):.*?return render_template\(\'order_confirmation\.html\', order=order\)'
        confirmation_replacement = '''@app.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    try:
        # Use our resilient get_order_by_id function
        order = get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Check permission if it's a regular Order object
        if hasattr(order, 'customer_id') and order.customer_id != current_user.id and not current_user.is_admin:
            abort(403)
            
        return render_template('order_confirmation.html', order=order)
    except Exception as e:
        logger.error(f"Error loading order confirmation for order {order_id}: {str(e)}")
        flash(f"Error loading order details: {str(e)}", 'error')
        return redirect(url_for('index'))'''
        
        modified_content = re.sub(confirmation_pattern, confirmation_replacement, modified_content, flags=re.DOTALL)
        
        return modified_content
    except Exception as e:
        logger.error(f"Error updating order routes: {str(e)}")
        return content

def apply_changes():
    """Apply all changes to app.py"""
    try:
        # First backup the file
        backup_app()
        
        # Read the content
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Apply changes
        content = update_imports()
        if not content:
            logger.error("Failed to update imports")
            return False
            
        content = update_get_order_by_id(content)
        content = update_create_order_function(content)
        content = update_order_routes(content)
        
        # Write the updated content
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(content)
            
        logger.info("Successfully updated app.py")
        return True
    except Exception as e:
        logger.error(f"Error applying changes: {str(e)}")
        return False

if __name__ == "__main__":
    apply_changes() 