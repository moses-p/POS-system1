"""
Copy this function into app.py at the appropriate place (after the staff_order_detail route)
to add the missing route for staff_update_order_status
"""

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