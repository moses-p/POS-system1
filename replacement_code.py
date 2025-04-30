# Section 1: Fix for lines around 958-961
CODE_SECTION_1 = """                    # Use get_order_by_id for more resilient order retrieval
                    order = get_order_by_id(order.id)
                    if order:
                        return redirect(url_for('print_receipt', order_id=order.id))
                    else:
                        flash('Order was created but could not be retrieved. Please check orders list.', 'warning')
                        return redirect(url_for('index'))"""

# Section 2: Replacement for print_receipt function
CODE_SECTION_2 = """@app.route('/receipt/<int:order_id>')
def print_receipt(order_id):
    try:
        # Use our resilient get_order_by_id function
        order = get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Ensure order_date is properly formatted for template
        if hasattr(order, 'order_date') and isinstance(order.order_date, str):
            try:
                from datetime import datetime
                order.order_date = datetime.strptime(order.order_date, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # If we can't convert, keep it as a string - template has been updated to handle this
                pass
            
        # Add tax rate for receipt calculations
        tax_rate = 0.18  # 18% VAT
        # Pass current_user to template even for anonymous users
        return render_template('receipt.html', order=order, tax_rate=tax_rate, current_user=current_user)
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index'))"""

# Section 3: Replacement for order_confirmation function
CODE_SECTION_3 = """@app.route('/order/<int:order_id>')
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
        return redirect(url_for('index'))"""

# Section 4: Replacement for create_order function
CODE_SECTION_4 = """def create_order(customer_data, items_data, order_type):
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
        return None, f"Error creating order: {str(e)}\""""

def write_to_file():
    with open("section1.txt", "w") as f:
        f.write(CODE_SECTION_1)
    
    with open("section2.txt", "w") as f:
        f.write(CODE_SECTION_2)
    
    with open("section3.txt", "w") as f:
        f.write(CODE_SECTION_3)
    
    with open("section4.txt", "w") as f:
        f.write(CODE_SECTION_4)
    
    print("Created replacement code in section*.txt files")

if __name__ == "__main__":
    write_to_file() 