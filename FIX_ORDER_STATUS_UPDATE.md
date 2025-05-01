# Fix for 405 Method Not Allowed Error on Order Status Update

The error occurs because the route to handle order status updates (`staff_update_order_status`) is missing in the application code, but the form in the template is trying to use it.

## Steps to Fix

1. **Add the Missing Route**

Add the following code to `app.py` after the `staff_order_detail` function:

```python
@app.route('/staff/update_order_status/<int:order_id>', methods=['POST'])
@login_required
@staff_required
def staff_update_order_status(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # Get the new status from form
        new_status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        # Validate status
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('staff_order_detail', order_id=order_id))
        
        # Update the order status
        old_status = order.status
        order.status = new_status
        
        # Update timestamps based on status
        now = datetime.utcnow()
        order.updated_at = now
        
        if new_status == 'completed' and old_status != 'completed':
            order.completed_at = now
        
        # Save changes
        db.session.commit()
        
        flash(f'Order status updated to {new_status}', 'success')
        return redirect(url_for('staff_order_detail', order_id=order_id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating order status: {str(e)}")
        flash(f"Error updating order: {str(e)}", "error")
        return redirect(url_for('staff_order_detail', order_id=order_id))
```

2. **Update the `staff_order_detail` function** 

Modify the `return` statement in the `staff_order_detail` function to include the URL for the update form.

Find this line near the end of the function:
```python
return render_template('staff/order_detail.html', order=order, tax_rate=tax_rate)
```

And change it to:
```python
return render_template('staff/order_detail.html', order=order, tax_rate=tax_rate,
                      staff_update_order_status_url=url_for('staff_update_order_status', order_id=order_id))
```

3. **Restart the Application**

After making these changes, restart the Flask application to apply them.

## Verification

After implementing these changes, the order status update form should work correctly, without the 405 Method Not Allowed error. 