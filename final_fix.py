import sqlite3
import os
import time
import re
import shutil

print("===========================================")
print("EMERGENCY DATABASE FIX - DIRECT SCHEMA EDIT")
print("===========================================")

# Connect to the database with foreign keys disabled
db_path = 'instance/pos.db'
print(f"Connecting to database at {db_path}...")

# Backup the database first
backup_path = f'instance/pos_backup_{int(time.time())}.db'
try:
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to {backup_path}")
except Exception as e:
    print(f"Warning: Backup failed - {str(e)}")

# Connect with foreign_keys OFF for schema operations
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys=OFF;")
cursor = conn.cursor()

try:
    # Check if the problematic columns exist
    cursor.execute("PRAGMA table_info('order')")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"Current columns in order table: {column_names}")
    
    # SOLUTION 1: Try direct modification of the view in sqlite_master
    print("\n[APPROACH 1] Directly modifying SQL schema in sqlite_master...")
    
    # Get the current CREATE TABLE statement
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='order'")
    create_stmt = cursor.fetchone()[0]
    print(f"Original create statement: {create_stmt}")
    
    # See if we need to add viewed columns
    need_viewed = 'viewed' not in column_names
    need_viewed_at = 'viewed_at' not in column_names
    
    # Modify the create statement to include the new columns
    if need_viewed or need_viewed_at:
        # Remove the closing parenthesis
        new_stmt = create_stmt.rstrip(')')
        
        # Add the viewed column if needed
        if need_viewed:
            new_stmt += ', viewed BOOLEAN DEFAULT 0'
        
        # Add the viewed_at column if needed
        if need_viewed_at:
            new_stmt += ', viewed_at TIMESTAMP'
        
        # Add the closing parenthesis back
        new_stmt += ')'
        
        print(f"Modified create statement: {new_stmt}")
        
        # Apply the schema changes through a complete rebuild
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION;")
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # First backup all data
            backup_data = {}
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence' and not table_name.startswith('sqlite_'):
                    cursor.execute(f"SELECT * FROM '{table_name}'")
                    backup_data[table_name] = cursor.fetchall()
                    
                    # Get column names
                    cursor.execute(f"PRAGMA table_info('{table_name}')")
                    backup_data[f"{table_name}_cols"] = [col[1] for col in cursor.fetchall()]
            
            # Drop all existing tables (excluding system tables)
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence' and not table_name.startswith('sqlite_'):
                    cursor.execute(f"DROP TABLE IF EXISTS '{table_name}'")
            
            # Get all CREATE statements
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
            create_stmts = cursor.fetchall()
            
            # Recreate tables with modified statements
            for table_name, stmt in create_stmts:
                if table_name != 'sqlite_sequence' and not table_name.startswith('sqlite_'):
                    # Apply our modified statement for the order table
                    if table_name == 'order':
                        cursor.execute(new_stmt)
                    else:
                        cursor.execute(stmt)
            
            # Restore data to all tables
            for table_name in backup_data:
                if not table_name.endswith('_cols'):  # Skip column metadata
                    data = backup_data[table_name]
                    cols = backup_data.get(f"{table_name}_cols")
                    
                    if data and cols:
                        placeholders = ','.join(['?'] * len(cols))
                        cols_str = ','.join(cols)
                        
                        for row in data:
                            # Only insert values for columns that exist
                            cursor.execute(f"INSERT INTO '{table_name}' ({cols_str}) VALUES ({placeholders})", row)
            
            # Create appropriate indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON 'order' (order_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON 'order' (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_viewed ON 'order' (viewed)")
            
            # Commit the transaction
            cursor.execute("COMMIT;")
            print("Schema changes applied successfully!")
            
        except Exception as rebuild_err:
            print(f"Error during schema rebuild: {str(rebuild_err)}")
            cursor.execute("ROLLBACK;")
            raise rebuild_err
    else:
        print("Both columns already exist in the schema.")

    # SOLUTION 2: Full rebuild of just the order table
    print("\n[APPROACH 2] Creating a fresh order table...")
    
    try:
        # Create a new order table with a temporary name
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
        
        # Copy data from the old table
        column_list = ", ".join([col for col in column_names if col != "viewed" and col != "viewed_at"])
        cursor.execute(f"INSERT INTO order_new ({column_list}) SELECT {column_list} FROM 'order'")
        print(f"Copied {cursor.rowcount} orders to new table")
        
        # Set viewed=1 for all existing orders
        cursor.execute("UPDATE order_new SET viewed = 1")
        
        # Rename tables
        cursor.execute("DROP TABLE IF EXISTS order_old")
        cursor.execute("ALTER TABLE 'order' RENAME TO order_old")
        cursor.execute("ALTER TABLE order_new RENAME TO 'order'")
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON 'order' (order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON 'order' (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_viewed ON 'order' (viewed)")
        
        # Verify the new schema
        cursor.execute("PRAGMA table_info('order')")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]
        print(f"New columns in order table: {new_column_names}")
        
        # Check if solution 2 worked
        if 'viewed' in new_column_names and 'viewed_at' in new_column_names:
            print("Solution 2: Table rebuild successful!")
            conn.commit()
        else:
            print("Solution 2: Columns still missing!")
            conn.rollback()
            
    except Exception as e:
        print(f"Error in solution 2: {str(e)}")
        conn.rollback()
    
    # SOLUTION 3: Reset the viewed column in the database
    print("\n[APPROACH 3] Creating a standalone orders view query...")
    cursor.execute('''
    CREATE VIEW IF NOT EXISTS orders_view AS
    SELECT 
      o.id, 
      o.customer_id,
      o.order_date,
      o.total_amount,
      o.status,
      o.customer_name,
      o.customer_phone,
      o.customer_email,
      o.customer_address,
      o.order_type,
      o.created_by_id,
      o.updated_at,
      o.completed_at,
      CASE WHEN o.viewed IS NULL THEN 0 ELSE o.viewed END as viewed,
      o.viewed_at
    FROM "order" o
    ''')
    
    print("Created orders_view as a fallback")
    
    # Final checks
    cursor.execute("PRAGMA table_info('order')")
    final_columns = cursor.fetchall()
    final_column_names = [col[1] for col in final_columns]
    print(f"\nFinal columns in 'order' table: {final_column_names}")
    
    conn.commit()
    print("\n✓ Database changes applied successfully!")

except Exception as e:
    conn.rollback()
    print(f"\nERROR: {str(e)}")
finally:
    # Make sure foreign keys are turned back on
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.close()
    print("\nDatabase connection closed.")
    
print("\nIMPORTANT: Please restart the Flask server to use the updated schema.")
print(f"If issues persist, restore from backup: {backup_path}")

def fix_indentation(filename):
    """Fix indentation issues in a Python file"""
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    fixed_lines = []
    current_indent = 0
    in_multiline_string = False
    string_delimiter = None
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append(line)
            continue
        
        # Check for multiline strings
        if not in_multiline_string:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_multiline_string = True
                string_delimiter = stripped[:3]
                if stripped.endswith(string_delimiter) and len(stripped) > 3:
                    in_multiline_string = False
        else:
            if stripped.endswith(string_delimiter):
                in_multiline_string = False
            fixed_lines.append(line)
            continue
        
        # Skip comments
        if stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        
        # If inside a multiline string, don't modify
        if in_multiline_string:
            fixed_lines.append(line)
            continue
        
        # Adjust indentation based on colons and brackets
        if stripped.endswith(':'):
            fixed_lines.append(line)
            current_indent += 4
        elif stripped == 'else:' or stripped.startswith('elif ') or stripped.startswith('except ') or stripped.startswith('finally:'):
            # For else/elif/except/finally, keep same indent as previous block
            fixed_lines.append(line)
        else:
            # Normal line, use current indentation
            fixed_lines.append(' ' * current_indent + stripped + '\n')
        
        # Check for dedent indicators
        if stripped.startswith('return ') or stripped.startswith('break') or stripped.startswith('continue'):
            current_indent = max(0, current_indent - 4)
    
    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(fixed_lines)


def replace_functions():
    """Replace problematic functions in app.py"""
    # Create a backup
    shutil.copy('app.py', 'app.py.final_backup')
    
    with open('app.py', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace create_order function
    create_order_pattern = r'def create_order\(customer_data, items_data, order_type\):.*?(?=@app\.route|\ndef )'
    content = re.sub(create_order_pattern, CREATE_ORDER_FUNCTION, content, flags=re.DOTALL)
    
    # Replace catch_all function
    catch_all_pattern = r'@app\.route\(\'/<path:path>\'\).*?def catch_all\(path\):.*?(?=@app\.route|\ndef )'
    content = re.sub(catch_all_pattern, CATCH_ALL_FUNCTION, content, flags=re.DOTALL)
    
    # Replace get_order_by_id function
    get_order_pattern = r'def get_order_by_id\(order_id\):.*?(?=@app\.route|\ndef |\nif __name__)'
    content = re.sub(get_order_pattern, GET_ORDER_BY_ID_FUNCTION, content, flags=re.DOTALL)
    
    with open('app_fixed_final.py', 'w', encoding='utf-8') as file:
        file.write(content)
    
    print("Replaced problematic functions in app_fixed_final.py")
    return 'app_fixed_final.py'


if __name__ == "__main__":
    output_file = replace_functions()
    print("Verifying syntax...")
    
    try:
        import py_compile
        py_compile.compile(output_file, doraise=True)
        print("Syntax OK! Fixed app saved to app_fixed_final.py")
        # Copy to app.py if syntax is correct
        shutil.copy(output_file, 'app.py')
        print("Copied fixed app to app.py")
    except py_compile.PyCompileError as e:
        print(f"Syntax errors still exist: {str(e)}")
        print("The fixed version is available in app_fixed_final.py for manual inspection") 