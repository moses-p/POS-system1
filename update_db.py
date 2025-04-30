import sqlite3
from app import app, db, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    print("Updating database schema...")
    
    # First, try with SQLAlchemy through Flask app context
    try:
        with app.app_context():
            # Try to access the new column to see if it exists
            try:
                User.query.filter_by(is_staff=True).first()
                print("Schema is already up to date (is_staff column exists).")
            except Exception as e:
                print(f"Adding is_staff column: {e}")
                # Use SQLite to add the column
                db.session.execute('ALTER TABLE user ADD COLUMN is_staff BOOLEAN DEFAULT FALSE')
                db.session.commit()
                print("Schema updated successfully - added is_staff column.")
    except Exception as e:
        print(f"Error with SQLAlchemy update: {e}")
        
        # Fall back to direct SQLite
        try:
            # Connect to the database
            conn = sqlite3.connect('instance/pos.db')
            cursor = conn.cursor()
            
            # Check if is_staff column already exists
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'is_staff' not in column_names:
                # Add the is_staff column
                cursor.execute('ALTER TABLE user ADD COLUMN is_staff BOOLEAN DEFAULT 0')
                conn.commit()
                print("is_staff column added successfully using direct SQLite!")
            else:
                print("is_staff column already exists")
            
            # Check if reference_number column exists in order table
            cursor.execute("PRAGMA table_info('order')")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'reference_number' not in column_names:
                logger.info("Adding reference_number column to order table")
                cursor.execute('''
                    ALTER TABLE "order" 
                    ADD COLUMN reference_number VARCHAR(50) UNIQUE NULL
                ''')
                
                # Update existing orders with a reference number
                cursor.execute("SELECT id FROM 'order'")
                orders = cursor.fetchall()
                for order in orders:
                    order_id = order[0]
                    ref_num = f"ORD-MIGRATED-{order_id}"
                    cursor.execute(
                        "UPDATE 'order' SET reference_number = ? WHERE id = ?", 
                        (ref_num, order_id)
                    )
                
                logger.info(f"Added reference_number to {len(orders)} existing orders")
            else:
                logger.info("reference_number column already exists")
            
            # Close the connection
            conn.commit()
            logger.info("Database schema update completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating database schema: {str(e)}")
            return False
    finally:
        if 'conn' in locals():
            conn.close()
    
    print("Database update complete.")

def update_db():
    result = update_schema()
    if result:
        print("Database updated successfully")
    else:
        print("Database update failed")

if __name__ == '__main__':
    update_db() 