import sqlite3
import os
import time
from datetime import datetime

print("===========================================")
print("   SCHEMA FIX WITH REFRESHED SQLALCHEMY   ")
print("===========================================")

# Connect to the database
db_path = 'instance/pos.db'
print(f"Connecting to database at {db_path}...")

# Backup the database first
backup_path = f'instance/pos_backup_{int(time.time())}.db'
try:
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to {backup_path}")
except Exception as e:
    print(f"Warning: Backup failed - {str(e)}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("\nStep 1: Verifying current schema...")
    cursor.execute("PRAGMA table_info('order')")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"Current 'order' table columns: {column_names}")
    
    # Check if the viewed column exists but might be hidden or corrupted
    has_viewed = 'viewed' in column_names
    has_viewed_at = 'viewed_at' in column_names
    
    if not has_viewed or not has_viewed_at:
        print("\nStep 2: Rebuilding the order table...")
        
        # Create a temporary table with the correct schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS "order_new" (
            id INTEGER PRIMARY KEY,
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
        
        # Copy all existing data
        try:
            # For columns that exist in both tables
            common_columns = [col for col in column_names if col != 'viewed' and col != 'viewed_at']
            column_list = ", ".join(common_columns)
            
            print(f"Step 3: Copying data with columns: {column_list}")
            cursor.execute(f"INSERT INTO order_new ({column_list}) SELECT {column_list} FROM 'order'")
            print(f"Copied {cursor.rowcount} rows to new table")
            
            # Set all existing orders as viewed=1 
            cursor.execute("UPDATE order_new SET viewed = 1, viewed_at = ?", (datetime.now().isoformat(),))
            print(f"Marked {cursor.rowcount} existing orders as viewed")
            
            # Replace the old table with the new one
            print("Step 4: Replacing old table with new one")
            cursor.execute("DROP TABLE 'order'")
            cursor.execute("ALTER TABLE order_new RENAME TO 'order'")
            
            # Re-create indexes
            print("Step 5: Creating indexes")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON 'order' (order_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON 'order' (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_viewed ON 'order' (viewed)")
            
            # Commit the changes
            conn.commit()
            
        except Exception as data_err:
            conn.rollback()
            print(f"Error copying data: {str(data_err)}")
            raise
    else:
        print("Columns already exist in schema, attempting to repair...")
        # Try to force SQLAlchemy to recognize the columns by setting values explicitly
        cursor.execute("UPDATE 'order' SET viewed = 1, viewed_at = ? WHERE viewed IS NULL", (datetime.now().isoformat(),))
        print(f"Updated {cursor.rowcount} rows with NULL viewed values")
        conn.commit()
    
    # Final verification
    print("\nFinal schema verification:")
    cursor.execute("PRAGMA table_info('order')")
    final_columns = cursor.fetchall()
    final_column_names = [col[1] for col in final_columns]
    print(f"Final 'order' table columns: {final_column_names}")
    
    if 'viewed' in final_column_names and 'viewed_at' in final_column_names:
        print("\n✓ Fix completed successfully!")
        
        # Test to see if we can query the viewed column
        try:
            cursor.execute("SELECT COUNT(*) FROM 'order' WHERE viewed = 0")
            unviewed_count = cursor.fetchone()[0]
            print(f"Unviewed orders: {unviewed_count}")
            
            # Create a test unviewed order to verify notification works
            cursor.execute('''
            INSERT INTO 'order' (
                total_amount, 
                status, 
                order_type, 
                customer_name, 
                viewed, 
                order_date
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                999.99, 
                'pending', 
                'online', 
                'TEST ORDER - Please delete', 
                0, 
                datetime.now().isoformat()
            ))
            test_id = cursor.lastrowid
            print(f"Created test order #{test_id} with viewed=0 to verify notifications")
            conn.commit()
            
        except Exception as test_err:
            print(f"Error during testing: {str(test_err)}")
    else:
        print("❌ Fix failed - columns still missing!")

except Exception as e:
    conn.rollback()
    print(f"Error: {str(e)}")
finally:
    conn.close()
    print("\nDatabase connection closed.")
    
print("\nIMPORTANT NEXT STEPS:")
print("1. Restart the Flask application")
print("2. Clear your browser cache")
print("3. Test the staff interface")
print(f"4. If issues persist, restore from backup: {backup_path}") 