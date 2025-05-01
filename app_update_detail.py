from flask import render_template, url_for

def staff_order_detail(order_id):
    order = get_order_by_id(order_id)
    tax_rate = calculate_tax_rate(order)
    return render_template('staff/order_detail.html', order=order, tax_rate=tax_rate,
                          staff_update_order_status_url=url_for('staff_update_order_status', order_id=order_id)) 