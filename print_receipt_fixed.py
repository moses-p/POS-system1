"""
This file contains a fixed version of the print_receipt function 
that uses raw SQL queries to retrieve orders correctly.
"""

@app.route('/receipt/<int:order_id>')
def print_receipt(order_id):
    """Generate receipt for an order"""
    try:
        # Use raw SQL instead of ORM to avoid reference_number column issues
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT id, customer_name, order_date, total_amount, status,
                  customer_phone, customer_email, customer_address,
                  order_type, created_by_id
            FROM "order"
            WHERE id = ?
        """, (order_id,))
        
        order_data = cursor.fetchone()
        if not order_data:
            conn.close()
            flash(f"Order with ID {order_id} not found", "danger")
            return redirect(url_for('index'))
        
        # Get order items
        cursor.execute("""
            SELECT oi.id, oi.product_id, oi.quantity, oi.price,
                  p.name as product_name
            FROM order_item oi
            JOIN product p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        
        items = []
        for item_row in cursor.fetchall():
            item = SimpleNamespace(
                id=item_row[0],
                product_id=item_row[1],
                quantity=item_row[2],
                price=item_row[3],
                product=SimpleNamespace(name=item_row[4]),
                subtotal=item_row[2] * item_row[3]  # Calculate subtotal
            )
            items.append(item)
        
        # Get staff name if it was created by staff
        staff_name = "Online Order"
        if order_data[9]:  # created_by_id
            cursor.execute("SELECT username FROM user WHERE id = ?", (order_data[9],))
            staff_row = cursor.fetchone()
            if staff_row:
                staff_name = staff_row[0]
        
        # Create order object
        order = SimpleNamespace(
            id=order_data[0],
            customer_name=order_data[1] or "Guest",
            order_date=order_data[2],
            total_amount=order_data[3],
            status=order_data[4],
            customer_phone=order_data[5],
            customer_email=order_data[6],
            customer_address=order_data[7],
            order_type=order_data[8],
            created_by_id=order_data[9],
            items=items
        )
        
        conn.close()
        
        # Add tax rate for receipt calculations
        tax_rate = app.config.get('TAX_RATE', 0.0)
        
        return render_template('receipt.html', order=order, tax_rate=tax_rate, current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index')) 