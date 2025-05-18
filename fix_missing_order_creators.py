from app import app, db, Order, User
from sqlalchemy import or_
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_missing_order_creators():
    with app.app_context():
        # Get all staff users
        staff_users = User.query.filter_by(is_staff=True).all()
        staff_by_email = {u.email.lower(): u for u in staff_users if u.email}
        staff_by_name = {u.full_name.lower(): u for u in staff_users if u.full_name}
        staff_by_initials = {u.initials.lower(): u for u in staff_users if u.initials}
        default_staff = staff_users[0] if staff_users else None

        # Find orders with missing created_by_id
        orders = Order.query.filter(or_(Order.created_by_id == None, Order.created_by_id == 0)).all()
        logger.info(f"Found {len(orders)} orders with missing created_by_id.")
        updated = 0
        for order in orders:
            matched_user = None
            # Try match by email
            if order.customer_email and order.customer_email.lower() in staff_by_email:
                matched_user = staff_by_email[order.customer_email.lower()]
            # Try match by full name
            elif order.customer_name and order.customer_name.lower() in staff_by_name:
                matched_user = staff_by_name[order.customer_name.lower()]
            # Try match by initials in customer_name
            elif order.customer_name:
                for initials, user in staff_by_initials.items():
                    if initials in order.customer_name.lower():
                        matched_user = user
                        break
            # If still not matched, assign to default staff
            if not matched_user and default_staff:
                matched_user = default_staff
                logger.info(f"Order {order.id}: forcibly assigned to default staff {default_staff.full_name} (ID {default_staff.id})")
            if matched_user:
                order.created_by_id = matched_user.id
                updated += 1
                logger.info(f"Order {order.id}: set created_by_id to {matched_user.id} ({matched_user.full_name})")
        db.session.commit()
        logger.info(f"Updated {updated} orders with missing created_by_id.")

if __name__ == "__main__":
    fix_missing_order_creators() 