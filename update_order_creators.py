from app import app, db
from models import Order, User, StaffActivity
from datetime import datetime
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('order_updates.log'),
        logging.StreamHandler()
    ]
)

def get_staff_at_time(order_time):
    """Find the staff member who was active at the given time"""
    # Find the most recent staff activity before the order time
    activity = StaffActivity.query.filter(
        StaffActivity.timestamp <= order_time
    ).order_by(StaffActivity.timestamp.desc()).first()
    
    if activity:
        # Get the staff member details
        staff = User.query.get(activity.user_id)
        if staff:
            return {
                'id': staff.id,
                'name': staff.full_name,
                'email': staff.email,
                'activity_time': activity.timestamp
            }
    return None

def update_order_creators(dry_run=False):
    with app.app_context():
        try:
            # Get all orders without created_by_id
            orders = Order.query.filter_by(created_by_id=None).all()
            logging.info(f"Found {len(orders)} orders without created_by_id")
            
            if dry_run:
                logging.info("DRY RUN MODE - No changes will be made to the database")
            
            updated_count = 0
            skipped_count = 0
            staff_stats = {}
            
            # Update each order
            for order in orders:
                # Get the staff member who was active when the order was created
                staff_info = get_staff_at_time(order.created_at)
                
                if staff_info:
                    if not dry_run:
                        order.created_by_id = staff_info['id']
                        order.updated_at = datetime.utcnow()
                    
                    # Update staff statistics
                    staff_id = staff_info['id']
                    if staff_id not in staff_stats:
                        staff_stats[staff_id] = {
                            'name': staff_info['name'],
                            'count': 0,
                            'orders': []
                        }
                    staff_stats[staff_id]['count'] += 1
                    staff_stats[staff_id]['orders'].append(order.id)
                    
                    logging.info(
                        f"{'[DRY RUN] ' if dry_run else ''}Order {order.id} "
                        f"(created at: {order.created_at}) will be assigned to "
                        f"staff member: {staff_info['name']} "
                        f"(last activity: {staff_info['activity_time']})"
                    )
                    updated_count += 1
                else:
                    logging.warning(
                        f"Could not determine staff member for order {order.id} "
                        f"(created at: {order.created_at})"
                    )
                    skipped_count += 1
            
            if not dry_run:
                # Commit the changes
                db.session.commit()
                logging.info(f"Successfully updated {updated_count} orders")
            else:
                logging.info(f"Dry run completed - {updated_count} orders would be updated")
            
            # Log staff statistics
            logging.info("\nStaff Assignment Statistics:")
            for staff_id, stats in staff_stats.items():
                logging.info(
                    f"Staff: {stats['name']} - {stats['count']} orders "
                    f"(Order IDs: {', '.join(map(str, stats['orders']))})"
                )
            
            if skipped_count > 0:
                logging.warning(f"Skipped {skipped_count} orders due to missing staff activity data")
            
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            if not dry_run:
                db.session.rollback()

def main():
    parser = argparse.ArgumentParser(description='Update order creators based on staff activity')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Run in dry-run mode (no database changes)')
    args = parser.parse_args()
    
    update_order_creators(dry_run=args.dry_run)

if __name__ == "__main__":
    main() 