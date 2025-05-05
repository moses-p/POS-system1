import sqlite3
import logging
from datetime import datetime
import os
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("db_fix.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def fix_order_table():
    print("Fixing order table to include all required columns...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    # Create a backup before making changes
    backup_path = f'instance/pos_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    print(f"Creating a backup at {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Just recreate the table regardless of current status
        cursor.execute("BEGIN TRANSACTION")
        
        # Check for existing orders
        cursor.execute("SELECT COUNT(*) FROM 'order'")
        order_count = cursor.fetchone()[0]
        print(f"Current order count: {order_count}")
        
        if order_count > 0:
            # Get the old table structure
            cursor.execute("PRAGMA table_info('order')")
            old_schema = cursor.fetchall()
            old_columns = [col[1] for col in old_schema]
            print(f"Current order table columns: {old_columns}")
            
            # Step 1: Rename the existing table
            cursor.execute("ALTER TABLE 'order' RENAME TO 'order_old'")
            
            # Step 2: Create a new table with all required columns
            cursor.execute('''
            CREATE TABLE "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_number TEXT UNIQUE,
                customer_id INTEGER,
                order_date TIMESTAMP,
                total_amount REAL NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                customer_name TEXT,
                customer_phone TEXT,
                customer_email TEXT,
                customer_address TEXT,
                order_type TEXT DEFAULT 'online',
                created_by_id INTEGER,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                viewed BOOLEAN DEFAULT 0,
                viewed_at TIMESTAMP,
                payment_status TEXT DEFAULT 'pending',
                payment_method TEXT DEFAULT 'cash'
            )
            ''')
            
            # Step 3: Copy existing data with default values for new columns
            # Get all orders from old table
            cursor.execute("SELECT * FROM 'order_old'")
            old_orders = cursor.fetchall()
            print(f"Migrating {len(old_orders)} orders from old table")
            
            for old_order in old_orders:
                # Create a dictionary of values from the old table
                old_order_dict = {old_columns[i]: old_order[i] for i in range(len(old_columns))}
                
                # Set defaults for required fields
                if 'order_date' not in old_order_dict or not old_order_dict.get('order_date'):
                    old_order_dict['order_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if 'reference_number' not in old_order_dict or not old_order_dict.get('reference_number'):
                    old_order_dict['reference_number'] = f"ORD-{datetime.now().strftime('%Y%m%d')}-{old_order_dict['id']}"
                
                # Build insert statement dynamically
                columns_to_insert = []
                values_to_insert = []
                
                # Include id
                columns_to_insert.append('id')
                values_to_insert.append(old_order_dict['id'])
                
                # Try to map all columns from old to new
                for col in ['reference_number', 'customer_name', 'customer_email', 'customer_phone', 
                           'customer_address', 'total_amount', 'status', 'payment_status', 'order_type', 
                           'updated_at', 'completed_at']:
                    if col in old_order_dict and old_order_dict[col] is not None:
                        columns_to_insert.append(col)
                        values_to_insert.append(old_order_dict[col])
                
                # Add created_at as order_date if needed
                if 'created_at' in old_order_dict and 'order_date' not in columns_to_insert:
                    columns_to_insert.append('order_date')
                    values_to_insert.append(old_order_dict['created_at'])
                
                # Build and execute the insert statement
                placeholders = ', '.join(['?' for _ in range(len(values_to_insert))])
                insert_sql = f"INSERT INTO 'order' ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
                cursor.execute(insert_sql, values_to_insert)
            
            # Drop old table
            cursor.execute("DROP TABLE 'order_old'")
            print("Successfully migrated orders to new table structure")
        else:
            # No orders - drop the existing table and create a fresh one
            cursor.execute("DROP TABLE IF EXISTS 'order'")
            print("Dropped existing empty order table")
            
            cursor.execute('''
            CREATE TABLE "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_number TEXT UNIQUE,
                customer_id INTEGER,
                order_date TIMESTAMP,
                total_amount REAL NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                customer_name TEXT,
                customer_phone TEXT,
                customer_email TEXT,
                customer_address TEXT,
                order_type TEXT DEFAULT 'online',
                created_by_id INTEGER,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                viewed BOOLEAN DEFAULT 0,
                viewed_at TIMESTAMP,
                payment_status TEXT DEFAULT 'pending',
                payment_method TEXT DEFAULT 'cash'
            )
            ''')
            print("Created fresh order table with all required columns")
        
        # Commit all changes
        conn.commit()
        
        # Verify the structure
        print("\nVerifying order table structure:")
        cursor.execute("PRAGMA table_info('order')")
        columns = cursor.fetchall()
        for column in columns:
            print(f"Column: {column[1]}, Type: {column[2]}")
        
        conn.close()
        print("\nFix completed! Please restart the application.")
    except Exception as e:
        print(f"Error fixing order table: {str(e)}")
        print("You can restore from the backup if needed.")

if __name__ == "__main__":
    fix_order_table() 