import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("db_fix.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def fix_order_table():
    """
    Fix the order table schema to ensure it matches what the code expects
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check current order table columns
        cursor.execute("PRAGMA table_info([order])")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"Current order table columns: {columns}")
        
        # Add missing columns if needed
        missing_columns = []
        required_columns = [
            'id', 'reference_number', 'customer_id', 'order_date', 'total_amount', 
            'status', 'customer_name', 'customer_phone', 'customer_email', 
            'customer_address', 'order_type', 'created_by_id', 'updated_at', 
            'completed_at', 'viewed', 'viewed_at'
        ]
        
        for column in required_columns:
            if column not in columns:
                missing_columns.append(column)
        
        if missing_columns:
            logger.info(f"Missing columns to add: {missing_columns}")
            
            # Add each missing column
            for column in missing_columns:
                if column == 'reference_number':
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} TEXT UNIQUE")
                elif column in ['customer_id', 'created_by_id']:
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} INTEGER")
                elif column in ['total_amount']:
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} REAL NOT NULL DEFAULT 0")
                elif column in ['viewed']:
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} BOOLEAN NOT NULL DEFAULT 0")
                elif column in ['order_date', 'updated_at', 'completed_at', 'viewed_at']:
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} TIMESTAMP")
                else:
                    cursor.execute(f"ALTER TABLE [order] ADD COLUMN {column} TEXT")
                
                logger.info(f"Added column: {column}")
            
            # Commit changes
            conn.commit()
            logger.info("Order table schema updated successfully")
        else:
            logger.info("Order table schema is already correct")
        
        # Close connection
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error fixing order table: {str(e)}")
        return False

if __name__ == "__main__":
    # Backup the database before making changes
    try:
        import shutil
        import os
        
        # Create backup directory if it doesn't exist
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        # Backup the database
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = 'instance/pos.db'
        target = f'backups/pos_backup_{timestamp}.db'
        
        if os.path.exists(source):
            shutil.copy2(source, target)
            logger.info(f"Database backed up to {target}")
        else:
            logger.warning("Database file not found, no backup created")
    except Exception as e:
        logger.error(f"Error backing up database: {str(e)}")
    
    # Fix the order table
    fix_order_table() 