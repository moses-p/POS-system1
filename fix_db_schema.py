import sqlite3
import os
from datetime import datetime

def rebuild_order_table():
    """Rebuild the order table completely to fix schema issues"""
    print("=== Starting Order Table Rebuild ===")
    
    # Connect to the database
    db_path = 'instance/pos.db'
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # STEP 1: Check for views that depend on the order table
        print("Checking for dependent views...")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view' AND sql LIKE '%order%'")
        dependent_views = cursor.fetchall()
        
        if dependent_views:
            print(f"Found {len(dependent_views)} views that depend on the order table:")
            for view_name, view_sql in dependent_views:
                print(f"- {view_name}")
                
            # Save view definitions for later recreation
            print("Dropping dependent views...")
            for view_name, _ in dependent_views:
                cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
                
        # STEP 2: Check the schema of the order table
        print("\nChecking order table schema...")
        cursor.execute("PRAGMA table_info([order])")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        print(f"Current columns: {column_names}")
        
        # STEP 3: Find the existing columns we want to keep
        existing_columns = []
        for col in columns_info:
            name = col[1]
            if name in ['id', 'customer_id', 'order_date', 'total_amount', 'status', 
                       'customer_name', 'customer_phone', 'customer_email', 'customer_address',
                       'order_type', 'created_by_id', 'updated_at', 'completed_at', 'viewed', 
                       'viewed_at', 'reference_number']:
                existing_columns.append(name)
        
        print(f"Columns to preserve: {existing_columns}")
        
        # STEP 4: Create a new order table with just the SQLAlchemy model columns
        print("\nCreating a new table with the correct schema...")
        cursor.execute("DROP TABLE IF EXISTS new_order")
        cursor.execute('''
        CREATE TABLE new_order (
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
            FOREIGN KEY (customer_id) REFERENCES user(id),
            FOREIGN KEY (created_by_id) REFERENCES user(id)
        )
        ''')
        
        # STEP 5: Copy data from old table to new table
        print("Copying data from old table to new table...")
        # Prepare columns string for the copy
        common_columns = [col for col in existing_columns]
        columns_str = ", ".join(common_columns)
        
        try:
            cursor.execute(f"INSERT INTO new_order ({columns_str}) SELECT {columns_str} FROM [order]")
            cursor.execute("SELECT COUNT(*) FROM new_order")
            copied_count = cursor.fetchone()[0]
            print(f"Copied {copied_count} orders with {len(common_columns)} columns")
        except Exception as e:
            print(f"Error copying data: {str(e)}")
            print("Attempting to copy orders one by one...")
            
            cursor.execute("SELECT id FROM [order]")
            order_ids = [row[0] for row in cursor.fetchall()]
            
            copied_count = 0
            for order_id in order_ids:
                try:
                    cursor.execute(f"INSERT INTO new_order ({columns_str}) SELECT {columns_str} FROM [order] WHERE id = ?", (order_id,))
                    copied_count += 1
                except Exception as e:
                    print(f"Error copying order {order_id}: {str(e)}")
            
            print(f"Copied {copied_count} out of {len(order_ids)} orders individually")
        
        # STEP 6: Rename tables to swap them
        print("\nSwapping tables...")
        cursor.execute("DROP TABLE IF EXISTS order_old")
        cursor.execute("ALTER TABLE [order] RENAME TO order_old")
        cursor.execute("ALTER TABLE new_order RENAME TO [order]")
        
        # STEP 7: Create indexes on the new table
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON [order] (order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON [order] (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_customer_id ON [order] (customer_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_order_reference_number ON [order] (reference_number)")
        
        # STEP 8: Generate reference numbers for any orders that don't have them
        cursor.execute("SELECT id FROM [order] WHERE reference_number IS NULL")
        null_ref_orders = cursor.fetchall()
        
        if null_ref_orders:
            print(f"Generating reference numbers for {len(null_ref_orders)} orders")
            for order_id in null_ref_orders:
                order_id = order_id[0]
                # Generate a unique reference number
                ref_number = f"ORD-FIXED-{order_id}"
                cursor.execute("UPDATE [order] SET reference_number = ? WHERE id = ?", (ref_number, order_id))
                
        # Commit changes before recreating views
        conn.commit()
        
        # STEP 9: Recreate the views that depend on the order table
        if dependent_views:
            print("\nRecreating dependent views...")
            for view_name, view_sql in dependent_views:
                try:
                    # Skip the safe_orders view that was causing issues
                    if view_name == 'safe_orders':
                        print(f"Skipping view {view_name} due to schema changes")
                        continue
                    
                    # For other views, try to recreate them
                    print(f"Recreating view {view_name}...")
                    cursor.execute(view_sql)
                except Exception as e:
                    print(f"Error recreating view {view_name}: {str(e)}")
        
        # Final commit
        conn.commit()
        print("\nOrder table rebuild completed successfully!")
        
        # Verify the table has all required columns
        cursor.execute("PRAGMA table_info([order])")
        final_columns = [col[1] for col in cursor.fetchall()]
        print(f"Final order table columns: {final_columns}")
        
        return True
        
    except Exception as e:
        print(f"Error rebuilding order table: {str(e)}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    rebuild_order_table() 