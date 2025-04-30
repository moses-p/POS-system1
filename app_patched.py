"""
This file contains the patch to be applied to app.py.
Replace the create_order function in app.py with this version.
"""

from sqlalchemy.exc import SQLAlchemyError
from create_order_direct import direct_create_order

def create_order(customer_data, items_data, order_type):
    """
    Centralized function to create orders from different contexts
    
    Parameters:
    - customer_data: dict with customer info (name, email, phone, address)
    - items_data: list of dicts with item info (product_id, quantity, price, name)
    - order_type: string indicating order source ('online', 'in-store', 'offline-sync')
    
    Returns:
    - (order, None) on success
    - (None, error_message) on error
    - (order, error_message) for duplicate orders
    """
    try:
        # Try using SQLAlchemy first
        try:
            # Validate inputs
            if not items_data:
                return None, "No items provided for the order"
            
            # Check for duplicate order (prevent double-submissions)
            # Look for identical orders in the last 10 minutes
            recent_time = datetime.utcnow() - timedelta(minutes=10)
            
            # For the same customer and similar total amount
            customer_id = customer_data.get('customer_id')
            customer_name = customer_data.get('customer_name', '')
            customer_email = customer_data.get('customer_email', '')
            
            # Calculate expected total amount
            total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in items_data)
            
            # Look for potential duplicates using direct SQL instead of ORM
            conn = db.engine.raw_connection()
            cursor = conn.cursor()
            
            # Format timestamp for SQLite
            recent_time_str = recent_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Base query
            query = "SELECT id, total_amount FROM 'order' WHERE order_date >= ?"
            params = [recent_time_str]
            
            # Add customer filters
            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)
            elif customer_email:
                query += " AND customer_email = ?"
                params.append(customer_email)
            elif customer_name:
                query += " AND customer_name = ?"
                params.append(customer_name)
            
            # Execute query
            cursor.execute(query, params)
            potential_duplicates = cursor.fetchall()
            
            duplicate_order = None
            
            # Check each potential duplicate more carefully
            for dup_id, dup_total in potential_duplicates:
                # Check if total amount is similar (within 5%)
                if abs(float(dup_total) - total_amount) / total_amount < 0.05:
                    # If the order seems to be a duplicate, return it with a warning
                    duplicate_order = Order.query.get(dup_id)
                    if duplicate_order:
                        return duplicate_order, "A duplicate order was detected"
            
            # Create new order with customer data using SQLAlchemy
            try:
                order = Order(
                    customer_id=customer_data.get('customer_id'),
                    customer_name=customer_data.get('customer_name', ''),
                    customer_phone=customer_data.get('customer_phone', ''),
                    customer_email=customer_data.get('customer_email', ''),
                    customer_address=customer_data.get('customer_address', ''),
                    total_amount=total_amount,
                    order_type=order_type,
                    created_by_id=current_user.id if current_user.is_authenticated else None,
                    status='pending'
                )
                
                db.session.add(order)
                db.session.flush()
                
                # Add order items
                for item_data in items_data:
                    product_id = item_data.get('product_id')
                    quantity = item_data.get('quantity', 1)
                    price = item_data.get('price', 0)
                    
                    # Get product to update stock
                    product = Product.query.get(product_id)
                    if product:
                        # Create order item
                        order_item = OrderItem(
                            order_id=order.id,
                            product_id=product_id,
                            quantity=quantity,
                            price=price
                        )
                        db.session.add(order_item)
                        
                        # Update product stock
                        product.update_stock(quantity, 'sale')
                
                # Generate a reference number (e.g., ORD-{year}{month}{day}-{id})
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
                raise e
                
        except SQLAlchemyError as e:
            # Fall back to direct SQL approach
            logger.warning(f"Falling back to direct SQL for order creation due to: {str(e)}")
            order_id, reference = direct_create_order(customer_data, items_data, order_type)
            
            if order_id:
                # Get the order using the ID
                order = Order.query.get(order_id)
                if order:
                    return order, None
                else:
                    # If we can't get the order through SQLAlchemy, create a simple object with the essential info
                    logger.warning(f"Created order {order_id} with direct SQL but can't access through ORM")
                    class SimpleOrder:
                        def __init__(self, id, reference_number):
                            self.id = id
                            self.reference_number = reference_number
                    
                    return SimpleOrder(order_id, reference), None
            else:
                return None, reference  # reference contains the error message
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating order: {str(e)}")
        return None, f"Error creating order: {str(e)}" 