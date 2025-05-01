import sqlite3
import logging
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("schema_fix.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a database connection"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None

def check_column_exists(conn, table, column):
    """Check if a column exists in a table using a safer approach"""
    try:
        cursor = conn.cursor()
        # Use a SELECT statement that will fail if the column doesn't exist
        cursor.execute(f"SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name=?", (column,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"Error checking if column exists: {str(e)}")
        return False

def fix_reference_number_column():
    """Add or rebuild reference_number column to the Order table"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return False

        # Check if column already exists
        needs_column = not check_column_exists(conn, 'order', 'reference_number')
        
        cursor = conn.cursor()
        
        # If the column doesn't exist, add it
        if needs_column:
            try:
                logger.info("Adding reference_number column to order table")
                cursor.execute('ALTER TABLE "order" ADD COLUMN reference_number TEXT UNIQUE')
            except sqlite3.OperationalError as e:
                # If we get here, maybe the table name needs different quoting or escaping
                logger.warning(f"First approach failed: {str(e)}, trying an alternative")
                try:
                    cursor.execute('ALTER TABLE [order] ADD COLUMN reference_number TEXT UNIQUE')
                    logger.info("Added reference_number column to order table (using square brackets)")
                except sqlite3.OperationalError as e2:
                    logger.error(f"Failed to add column: {str(e2)}")
                    conn.close()
                    return False
        else:
            logger.info("reference_number column already exists in the order table")
            
            # Even if the column exists, check if any orders are missing reference numbers
            logger.info("Checking for orders without reference numbers")
            cursor.execute('SELECT COUNT(*) FROM "order" WHERE reference_number IS NULL')
            missing_refs = cursor.fetchone()[0]
            if missing_refs == 0:
                logger.info("All orders have reference numbers")
                conn.close()
                return True

        # Generate reference numbers for all orders with NULL reference_number
        try:
            cursor.execute('SELECT id, order_date FROM "order" WHERE reference_number IS NULL')
            orders = cursor.fetchall()
            
            # Update logic for adding reference numbers
            for order in orders:
                order_id = order['id']
                try:
                    order_date = datetime.strptime(order['order_date'], '%Y-%m-%d %H:%M:%S')
                    date_part = order_date.strftime('%Y%m%d')
                except:
                    date_part = datetime.now().strftime('%Y%m%d')
                    
                random_part = str(uuid.uuid4())[:8]
                reference_number = f"ORD-{date_part}-{random_part}"
                
                try:
                    cursor.execute('UPDATE "order" SET reference_number = ? WHERE id = ?', 
                                (reference_number, order_id))
                    logger.info(f"Updated order {order_id} with reference number {reference_number}")
                except sqlite3.OperationalError as e:
                    logger.error(f"Error updating order {order_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error generating reference numbers: {str(e)}")
            conn.rollback()
            conn.close()
            return False
                                
        conn.commit()
        conn.close()
        logger.info("Successfully updated reference_number column")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing reference_number column: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False

def fix_order_table_names():
    """Make sure order table columns match the ORM model"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return False
            
        cursor = conn.cursor()
        
        # List of expected column names in the order table
        expected_columns = [
            'id', 'reference_number', 'customer_id', 'order_date', 'total_amount', 
            'status', 'customer_name', 'customer_phone', 'customer_email', 
            'customer_address', 'order_type', 'created_by_id', 'updated_at', 
            'completed_at', 'viewed', 'viewed_at'
        ]
        
        # Get actual columns
        cursor.execute("PRAGMA table_info('order')")
        actual_columns = [row['name'] for row in cursor.fetchall()]
        
        logger.info(f"Actual columns in order table: {actual_columns}")
        
        # Check if any expected columns are missing
        missing_columns = [col for col in expected_columns if col not in actual_columns]
        
        if missing_columns:
            logger.info(f"Missing columns: {missing_columns}")
            
            # Add missing columns
            for column in missing_columns:
                try:
                    if column == 'reference_number':
                        cursor.execute('ALTER TABLE "order" ADD COLUMN reference_number TEXT UNIQUE')
                    elif column == 'viewed':
                        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed BOOLEAN DEFAULT FALSE')
                    elif column == 'viewed_at':
                        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed_at DATETIME')
                    elif column == 'updated_at':
                        cursor.execute('ALTER TABLE "order" ADD COLUMN updated_at DATETIME')
                    elif column == 'completed_at':
                        cursor.execute('ALTER TABLE "order" ADD COLUMN completed_at DATETIME')
                    else:
                        cursor.execute(f'ALTER TABLE "order" ADD COLUMN {column} TEXT')
                    
                    logger.info(f"Added column: {column}")
                except sqlite3.OperationalError as e:
                    logger.error(f"Error adding column {column}: {str(e)}")
        else:
            logger.info("Order table schema matches expected columns")
            
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error fixing order table: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False

# Add an alias function for backward compatibility
def add_reference_number_column():
    """Alias for fix_reference_number_column for backward compatibility"""
    logger.info("Called add_reference_number_column alias function")
    return fix_reference_number_column()

if __name__ == "__main__":
    logger.info("Starting database schema fix for reference_number column")
    
    success1 = fix_reference_number_column()
    success2 = fix_order_table_names()
    
    if success1 and success2:
        logger.info("Database schema updated successfully")
        print("Database schema updated successfully")
    else:
        logger.error("Failed to update database schema")
        print("Failed to update database schema, check schema_fix.log for details") 