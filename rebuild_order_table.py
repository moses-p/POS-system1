import sqlite3
import logging
import os
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("order_table_rebuild.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the database before making changes"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = 'instance/pos.db'
        target = f'instance/pos_backup_{timestamp}.db'
        
        if os.path.exists(source):
            shutil.copy2(source, target)
            logger.info(f"Database backed up to {target}")
            return True
        else:
            logger.warning("Database file not found, no backup created")
            return False
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def rebuild_order_table():
    """Completely rebuild the order table with correct schema"""
    try:
        # First backup the database
        if not backup_database():
            logger.warning("Proceeding without backup")
            
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check if there's existing data to migrate
        cursor.execute("SELECT COUNT(*) FROM 'order'")
        order_count = cursor.fetchone()[0]
        logger.info(f"Found {order_count} existing orders to migrate")
        
        # If there are existing orders, we need to back them up
        existing_orders = []
        existing_items = []
        
        if order_count > 0:
            # Get all existing orders
            cursor.execute("SELECT * FROM 'order'")
            existing_orders = cursor.fetchall()
            
            # Get column names for orders
            cursor.execute("PRAGMA table_info('order')")
            order_columns = [col[1] for col in cursor.fetchall()]
            
            # Get all existing order items
            cursor.execute("SELECT * FROM order_item")
            existing_items = cursor.fetchall()
            
            # Get column names for order items
            cursor.execute("PRAGMA table_info('order_item')")
            item_columns = [col[1] for col in cursor.fetchall()]
            
            logger.info(f"Backed up {len(existing_orders)} orders and {len(existing_items)} order items")
        
        # Drop existing order_item table (it has foreign key to order)
        logger.info("Dropping order_item table")
        cursor.execute("DROP TABLE IF EXISTS order_item")
        
        # Drop existing order table
        logger.info("Dropping order table")
        cursor.execute("DROP TABLE IF EXISTS 'order'")
        
        # Create new order table with correct schema
        logger.info("Creating new order table with correct schema")
        cursor.execute('''
        CREATE TABLE "order" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_number VARCHAR(50) UNIQUE,
            customer_id INTEGER,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount FLOAT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            customer_name VARCHAR(100),
            customer_phone VARCHAR(20),
            customer_email VARCHAR(100),
            customer_address TEXT,
            order_type VARCHAR(20) DEFAULT 'online',
            created_by_id INTEGER,
            updated_at TIMESTAMP,
            completed_at TIMESTAMP,
            viewed BOOLEAN DEFAULT 0,
            viewed_at TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES user(id),
            FOREIGN KEY (created_by_id) REFERENCES user(id)
        )
        ''')
        
        # Create new order_item table
        logger.info("Creating new order_item table")
        cursor.execute('''
        CREATE TABLE order_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price FLOAT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES "order"(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
        ''')
        
        # Create indexes
        logger.info("Creating indexes")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_customer_id ON \"order\" (customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON \"order\" (order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON \"order\" (status)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_order_reference_number ON \"order\" (reference_number)")
        
        # Restore data if we had existing orders
        if existing_orders:
            logger.info("Restoring order data")
            
            # Prepare the insert placeholders based on column count
            order_column_count = len(order_columns)
            order_placeholders = ', '.join(['?' for _ in range(order_column_count)])
            
            # Create a dynamic INSERT statement based on the columns we have
            order_insert_sql = f"INSERT INTO 'order' ({', '.join(order_columns)}) VALUES ({order_placeholders})"
            
            # Insert orders
            for order in existing_orders:
                try:
                    cursor.execute(order_insert_sql, order)
                except sqlite3.Error as e:
                    logger.warning(f"Error restoring order {order[0]}: {str(e)}")
            
            # Restore order items
            if existing_items:
                logger.info("Restoring order item data")
                
                # Prepare the insert placeholders based on column count
                item_column_count = len(item_columns)
                item_placeholders = ', '.join(['?' for _ in range(item_column_count)])
                
                # Create a dynamic INSERT statement based on the columns we have
                item_insert_sql = f"INSERT INTO order_item ({', '.join(item_columns)}) VALUES ({item_placeholders})"
                
                # Insert order items
                for item in existing_items:
                    try:
                        cursor.execute(item_insert_sql, item)
                    except sqlite3.Error as e:
                        logger.warning(f"Error restoring order item {item[0]}: {str(e)}")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        logger.info("Order table rebuild complete")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding order table: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    rebuild_order_table() 