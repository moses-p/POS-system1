@app.route('/receipt/<int:order_id>')
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
        return redirect(url_for('index')) 