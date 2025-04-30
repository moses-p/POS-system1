import sqlite3
import logging
import os
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("schema_fix.log"), logging.StreamHandler()]
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

def get_expected_schema():
    """Define the expected schema for all tables"""
    return {
        'user': [
            ('id', 'INTEGER', 1, None, 1),  # Primary key
            ('username', 'VARCHAR(80)', 1, None, 0),
            ('email', 'VARCHAR(120)', 1, None, 0),
            ('password_hash', 'VARCHAR(128)', 0, None, 0),
            ('is_admin', 'BOOLEAN', 0, '0', 0),
            ('is_staff', 'BOOLEAN', 0, '0', 0),
        ],
        'order': [
            ('id', 'INTEGER', 1, None, 1),  # Primary key
            ('reference_number', 'VARCHAR(50)', 0, None, 0),
            ('customer_id', 'INTEGER', 0, None, 0),
            ('order_date', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0),
            ('total_amount', 'FLOAT', 1, None, 0),
            ('status', 'VARCHAR(20)', 0, "'pending'", 0),
            ('customer_name', 'VARCHAR(100)', 0, None, 0),
            ('customer_phone', 'VARCHAR(20)', 0, None, 0),
            ('customer_email', 'VARCHAR(100)', 0, None, 0),
            ('customer_address', 'TEXT', 0, None, 0),
            ('order_type', 'VARCHAR(20)', 0, "'online'", 0),
            ('created_by_id', 'INTEGER', 0, None, 0),
            ('updated_at', 'TIMESTAMP', 0, None, 0),
            ('completed_at', 'TIMESTAMP', 0, None, 0),
            ('viewed', 'BOOLEAN', 0, '0', 0),
            ('viewed_at', 'TIMESTAMP', 0, None, 0),
            ('payment_method', 'VARCHAR(50)', 0, None, 0),
            ('payment_status', 'VARCHAR(50)', 0, None, 0),
            ('payment_id', 'VARCHAR(100)', 0, None, 0),
            ('delivery_address', 'TEXT', 0, None, 0),
        ],
        'product': [
            ('id', 'INTEGER', 1, None, 1),  # Primary key
            ('name', 'VARCHAR(100)', 1, None, 0),
            ('description', 'TEXT', 0, None, 0),
            ('price', 'FLOAT', 1, None, 0),
            ('currency', 'VARCHAR(3)', 1, "'UGX'", 0),
            ('stock', 'FLOAT', 1, '0', 0),
            ('max_stock', 'FLOAT', 1, '0', 0),
            ('reorder_point', 'FLOAT', 1, '0', 0),
            ('unit', 'VARCHAR(10)', 1, "'pcs'", 0),
            ('category', 'VARCHAR(50)', 0, None, 0),
            ('image_url', 'VARCHAR(200)', 0, None, 0),
            ('barcode', 'VARCHAR(50)', 0, None, 0),
            ('created_at', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0),
            ('updated_at', 'TIMESTAMP', 0, 'CURRENT_TIMESTAMP', 0),
        ]
    }

def fix_table_schema(table_name, expected_columns):
    """Fix the schema for a specific table"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        existing_columns = {col[1]: col for col in cursor.fetchall()}
        
        added_columns = 0
        for col_info in expected_columns:
            col_name = col_info[0]
            
            # Skip if it's the primary key or if column already exists
            if col_name == 'id' or col_name in existing_columns:
                continue
                
            col_type = col_info[1]
            col_notnull = "NOT NULL" if col_info[2] == 1 else ""
            col_default = f"DEFAULT {col_info[3]}" if col_info[3] is not None else ""
            
            # Build and execute the ALTER TABLE statement
            alter_sql = f"ALTER TABLE '{table_name}' ADD COLUMN {col_name} {col_type} {col_notnull} {col_default}"
            logger.info(f"Adding column '{col_name}' to table '{table_name}'")
            logger.debug(f"SQL: {alter_sql}")
            
            try:
                cursor.execute(alter_sql)
                added_columns += 1
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add column '{col_name}': {str(e)}")
        
        conn.commit()
        conn.close()
        
        if added_columns > 0:
            logger.info(f"Added {added_columns} columns to table '{table_name}'")
        else:
            logger.info(f"No columns needed to be added to table '{table_name}'")
            
        return added_columns
    except Exception as e:
        logger.error(f"Error fixing table '{table_name}': {str(e)}")
        return 0

def add_missing_indexes():
    """Add any missing indexes to the database"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Define the indexes we want to create
        indexes = [
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_username ON user (username)", "user.username unique"),
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_email ON user (email)", "user.email unique"),
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_order_reference_number ON \"order\" (reference_number)", "order.reference_number unique"),
            ("CREATE INDEX IF NOT EXISTS idx_order_customer_id ON \"order\" (customer_id)", "order.customer_id"),
            ("CREATE INDEX IF NOT EXISTS idx_order_date ON \"order\" (order_date)", "order.order_date"),
            ("CREATE INDEX IF NOT EXISTS idx_order_status ON \"order\" (status)", "order.status"),
            ("CREATE INDEX IF NOT EXISTS idx_product_name ON product (name)", "product.name"),
            ("CREATE INDEX IF NOT EXISTS idx_product_category ON product (category)", "product.category"),
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_product_barcode ON product (barcode)", "product.barcode unique"),
        ]
        
        for idx_sql, idx_name in indexes:
            try:
                cursor.execute(idx_sql)
                logger.info(f"Created/verified index: {idx_name}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Error creating index {idx_name}: {str(e)}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding indexes: {str(e)}")
        return False

def fix_all_tables():
    """Fix the schema for all tables"""
    # Backup database first
    if not backup_database():
        logger.warning("Proceeding without backup")
    
    # Get the expected schema
    schema = get_expected_schema()
    
    # Fix each table
    total_added = 0
    for table_name, expected_columns in schema.items():
        added = fix_table_schema(table_name, expected_columns)
        total_added += added
    
    # Add missing indexes
    add_missing_indexes()
    
    logger.info(f"Schema fix complete. Added {total_added} columns in total.")
    return total_added > 0

if __name__ == "__main__":
    fix_all_tables() 