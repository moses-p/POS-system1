import sqlite3
import logging
import os
import shutil
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("cart_fix.log"), logging.StreamHandler()]
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
    """Completely rebuild the order table with all required columns"""
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # First, create a backup of the database
        backup_database()
        
        # Check if orders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order'")
        table_exists = cursor.fetchone()
        
        # Extract existing data if the table exists
        order_data = []
        if table_exists:
            # Check existing columns
            cursor.execute("PRAGMA table_info('order')")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Get column names as string for SELECT statement
            column_names = ", ".join(columns)
            
            # Extract all data from existing table
            cursor.execute(f"SELECT {column_names} FROM \"order\"")
            order_data = cursor.fetchall()
            
            # Create a new table with _temp suffix
            logger.info("Creating temporary order table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "order_temp" (
                    id INTEGER PRIMARY KEY,
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
                    payment_method VARCHAR(50),
                    payment_status VARCHAR(50),
                    payment_id VARCHAR(100),
                    delivery_address TEXT
                )
            """)
            
            # Drop old order table
            logger.info("Dropping old order table")
            cursor.execute("DROP TABLE IF EXISTS \"order_old\"")
            
            if order_data:
                # Create placeholders for INSERT
                insert_placeholders = ", ".join(["?"] * len(columns))
                
                # Insert data into the new table
                for row in order_data:
                    try:
                        cursor.execute(f"INSERT INTO order_temp ({column_names}) VALUES ({insert_placeholders})", row)
                    except sqlite3.Error as e:
                        logger.warning(f"Error inserting row: {str(e)}")
                        continue
            
            # Rename tables
            logger.info("Renaming tables")
            cursor.execute("ALTER TABLE \"order\" RENAME TO \"order_old\"")
            cursor.execute("ALTER TABLE \"order_temp\" RENAME TO \"order\"")
            
            # Recreate foreign key relationships as needed
            # For order_item -> order
            cursor.execute("""
                UPDATE order_item SET order_id = NULL 
                WHERE order_id NOT IN (SELECT id FROM \"order\")
            """)
            
        else:
            # Create new order table if it doesn't exist
            logger.info("Creating new order table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "order" (
                    id INTEGER PRIMARY KEY,
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
                    payment_method VARCHAR(50),
                    payment_status VARCHAR(50),
                    payment_id VARCHAR(100),
                    delivery_address TEXT
                )
            """)
        
        # Create indexes
        logger.info("Creating indexes")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON \"order\" (order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON \"order\" (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_customer_id ON \"order\" (customer_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_order_reference_number ON \"order\" (reference_number)")
        
        # Generate reference numbers for any orders that don't have them
        cursor.execute("SELECT id FROM \"order\" WHERE reference_number IS NULL")
        null_ref_orders = cursor.fetchall()
        
        if null_ref_orders:
            logger.info(f"Generating reference numbers for {len(null_ref_orders)} orders")
            for order_id in null_ref_orders:
                order_id = order_id[0]
                # Generate a unique reference number using timestamp and order ID
                ref_number = f"ORD-{int(time.time())}-{order_id}"
                cursor.execute("UPDATE \"order\" SET reference_number = ? WHERE id = ?", (ref_number, order_id))
        
        # Verify the table has the reference_number column
        cursor.execute("PRAGMA table_info('order')")
        columns = [col[1] for col in cursor.fetchall()]
        
        logger.info(f"Order table columns: {columns}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("Order table rebuild completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding order table: {str(e)}")
        return False

def check_cart_queries():
    """Check and fix common cart queries"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Test the query that's used in the cart page
        try:
            cursor.execute("""
                SELECT id, reference_number, customer_id, order_date, total_amount, status
                FROM "order" 
                LIMIT 1
            """)
            logger.info("Cart query test successful")
        except sqlite3.OperationalError as e:
            logger.error(f"Cart query test failed: {str(e)}")
            logger.info("Rebuilding order table to fix cart queries")
            conn.close()
            return rebuild_order_table()
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking cart queries: {str(e)}")
        return False

def refresh_views():
    """Create or refresh views for cart operations"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Create a view for orders that safely handles missing columns
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS safe_orders AS
        SELECT 
            id, 
            COALESCE(reference_number, 'ORD-' || id) as reference_number,
            customer_id,
            order_date,
            total_amount,
            status,
            customer_name,
            customer_phone,
            customer_email,
            customer_address,
            order_type,
            created_by_id,
            updated_at,
            completed_at,
            COALESCE(viewed, 0) as viewed,
            viewed_at,
            payment_method,
            payment_status,
            payment_id
        FROM "order"
        """)
        
        # Update the view if needed
        cursor.execute("DROP VIEW IF EXISTS safe_orders")
        cursor.execute("""
        CREATE VIEW safe_orders AS
        SELECT 
            id, 
            COALESCE(reference_number, 'ORD-' || id) as reference_number,
            customer_id,
            order_date,
            total_amount,
            status,
            customer_name,
            customer_phone,
            customer_email,
            customer_address,
            order_type,
            created_by_id,
            updated_at,
            completed_at,
            COALESCE(viewed, 0) as viewed,
            viewed_at,
            COALESCE(payment_method, 'unknown') as payment_method,
            COALESCE(payment_status, 'unknown') as payment_status,
            payment_id
        FROM "order"
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database views refreshed successfully")
        return True
    except Exception as e:
        logger.error(f"Error refreshing views: {str(e)}")
        return False

def fix_cart_issues():
    """Fix issues with the cart page"""
    logger.info("Starting cart issue fix")
    
    # Check queries first
    if not check_cart_queries():
        # If initial query check fails, rebuild the order table
        if not rebuild_order_table():
            logger.error("Failed to fix cart issues - could not rebuild order table")
            return False
    
    # Create/refresh views for safe queries
    refresh_views()
    
    logger.info("Cart issue fix completed")
    return True

if __name__ == "__main__":
    fix_cart_issues() 