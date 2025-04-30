import shutil
import os
import py_compile
import re

# Functions with correct indentation
FIXED_FUNCTIONS = {
    'create_order': '''def create_order(customer_data, items_data, order_type):
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
        return None, f"Error creating order: {str(e)}"''',

    'catch_all': '''@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for any unhandled URLs"""
    logger.warning(f"Unhandled path requested: {path}")
    
    # Try to determine if this is a static file request
    if '.' in path:
        extension = path.split('.')[-1].lower()
        # If it seems to be a static file, try to serve it from static folder
        if extension in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'ico', 'svg', 'woff', 'woff2', 'ttf', 'eot']:
            try:
                # Check if file exists in static folder
                filepath = os.path.join(app.static_folder, path)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    return send_from_directory(app.static_folder, path)
            except Exception as e:
                logger.error(f"Error serving static file {path}: {e}")
                
    # If we reach here, it's not a valid route
    return redirect(url_for('index'))''',

    'get_order_by_id': '''def get_order_by_id(order_id):
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
            # Direct database query with LEFT JOIN to handle missing products
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
            
            # Get the order items with LEFT JOIN to products
            cursor.execute("""
                SELECT oi.*, p.name as product_name, p.price as product_price 
                FROM order_item oi
                LEFT JOIN product p ON oi.product_id = p.id
                WHERE oi.order_id = ?
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
                
        except Exception as inner_e:
            logger.error(f"Error in direct SQL retrieval: {str(inner_e)}")
            return None
        
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        return None'''
}

# Make a backup of the current file
src_file = 'app.py'
dst_file = 'app.py.comprehensive_backup'
shutil.copy(src_file, dst_file)
print(f"Created backup: {dst_file}")

# Read the current content
with open(src_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Define patterns to find the functions
patterns = {
    'create_order': r'def create_order\([^)]*\):[^}]*?(?=\n\w|$)',
    'catch_all': r'@app\.route\(\'/<path:path>\'\)\s*def catch_all\([^)]*\):[^}]*?(?=\n@|$)',
    'get_order_by_id': r'def get_order_by_id\([^)]*\):[^}]*?(?=\n\w|$)'
}

# Perform replacements
for func_name, pattern in patterns.items():
    if func_name in FIXED_FUNCTIONS:
        # Use re.DOTALL to match across newlines
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            print(f"Found function: {func_name}")
            content = content.replace(matches[0], FIXED_FUNCTIONS[func_name])
            print(f"Replaced function: {func_name}")
        else:
            print(f"Warning: Could not find pattern for {func_name}")

# Write the fixed content back
with open(src_file, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Wrote fixed functions to {src_file}")

# Check syntax
try:
    py_compile.compile(src_file, doraise=True)
    print("Syntax check passed!")
    print("The app has been fixed and should be ready to run.")
except py_compile.PyCompileError as e:
    print(f"Syntax errors still exist: {str(e)}")
    print("Restoring from backup...")
    shutil.copy(dst_file, src_file)
    print("Original file restored. You may need to try a different fix approach.") 