import sqlite3
import os
from datetime import datetime

print("===========================================")
print("REBUILDING ORDER TABLE WITH NEW COLUMNS")
print("===========================================")

# Connect to the database
db_path = 'instance/pos.db'
print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Step 1: Backup existing data
    print("Backing up existing orders...")
    cursor.execute("SELECT * FROM 'order'")
    orders = cursor.fetchall()
    print(f"Found {len(orders)} orders to back up")
    
    # Step 2: Get column names from the current table
    cursor.execute("PRAGMA table_info('order')")
    columns_info = cursor.fetchall()
    column_names = [col[1] for col in columns_info]
    column_types = {col[1]: col[2] for col in columns_info}
    print(f"Current order table has {len(column_names)} columns")
    
    # Step 3: Create a temporary backup table with the same schema
    print("Creating backup table...")
    cursor.execute("DROP TABLE IF EXISTS order_backup")
    
    # Generate CREATE TABLE statement for the backup table
    create_backup_sql = "CREATE TABLE order_backup ("
    for col in columns_info:
        name = col[1]
        type_str = col[2]
        not_null = "NOT NULL" if col[3] == 1 else ""
        default = f"DEFAULT {col[4]}" if col[4] is not None else ""
        pk = "PRIMARY KEY" if col[5] == 1 else ""
        create_backup_sql += f"{name} {type_str} {pk} {not_null} {default}, "
    # Remove trailing comma and space
    create_backup_sql = create_backup_sql[:-2] + ")"
    
    cursor.execute(create_backup_sql)
    
    # Step 4: Copy data to backup table
    if orders:
        placeholders = ",".join(["?" for _ in range(len(columns_info))])
        cursor.executemany(f"INSERT INTO order_backup VALUES ({placeholders})", orders)
    print(f"Copied {len(orders)} orders to backup table")
    
    # Step 5: Drop the original table
    print("Dropping original order table...")
    cursor.execute("DROP TABLE IF EXISTS 'order'")
    
    # Step 6: Create the new order table with all required columns
    print("Creating new order table with all required columns...")
    cursor.execute('''
    CREATE TABLE "order" (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER REFERENCES user(id),
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount FLOAT NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        customer_name VARCHAR(100),
        customer_phone VARCHAR(20),
        customer_email VARCHAR(100),
        customer_address TEXT,
        order_type VARCHAR(20) DEFAULT 'online',
        created_by_id INTEGER REFERENCES user(id),
        updated_at TIMESTAMP,
        completed_at TIMESTAMP,
        viewed BOOLEAN DEFAULT 0,
        viewed_at TIMESTAMP
    )
    ''')
    
    # Step 7: Determine which columns to copy from backup
    copy_columns = []
    for col in column_names:
        if col in ['id', 'customer_id', 'order_date', 'total_amount', 'status', 'customer_name', 
                  'customer_phone', 'customer_email', 'customer_address', 'order_type', 
                  'created_by_id', 'updated_at', 'completed_at']:
            copy_columns.append(col)
    
    # Step 8: Copy data from backup to new table
    if orders:
        columns_str = ", ".join(copy_columns)
        print(f"Restoring data with columns: {columns_str}")
        cursor.execute(f'''
        INSERT INTO "order" ({columns_str})
        SELECT {columns_str} FROM order_backup
        ''')
        print(f"Restored {cursor.rowcount} orders to new table")
    
    # Step 9: Set viewed=1 for all existing orders to avoid alarms
    cursor.execute('UPDATE "order" SET viewed = 1')
    print(f"Marked {cursor.rowcount} existing orders as viewed")
    
    # Step 10: Verify the new table has the correct schema
    cursor.execute("PRAGMA table_info('order')")
    new_columns = cursor.fetchall()
    new_column_names = [col[1] for col in new_columns]
    print(f"New order table has {len(new_column_names)} columns: {new_column_names}")
    
    # Check if the required columns are present
    if 'viewed' in new_column_names and 'viewed_at' in new_column_names:
        print("\n✓ TABLE REBUILD SUCCESSFUL!")
        
        # Step 11: Check for foreign key constraints and indexes
        cursor.execute("PRAGMA foreign_key_list('order')")
        fk_constraints = cursor.fetchall()
        if fk_constraints:
            print(f"Foreign key constraints restored: {len(fk_constraints)}")
        
        # Step 12: Create any needed indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON 'order' (order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON 'order' (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_viewed ON 'order' (viewed)")
        print("Created indexes on key columns")
        
        # Commit all changes
        conn.commit()
        
        # Clean up - drop the backup table
        cursor.execute("DROP TABLE IF EXISTS order_backup")
        conn.commit()
        print("Dropped backup table")
    else:
        print("\n✗ TABLE REBUILD FAILED - Missing required columns!")
        conn.rollback()
except Exception as e:
    print(f"\nERROR: {str(e)}")
    conn.rollback()
finally:
    # Close connection
    conn.close()
    print("\nDatabase connection closed.")
    
print("\nPlease restart the Flask server to use the updated schema.") 