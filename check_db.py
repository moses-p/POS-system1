import sqlite3
import os

print("Checking order table schema...")
conn = sqlite3.connect('instance/pos.db')
cursor = conn.cursor()

try:
    # Check if the order table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order'")
    if not cursor.fetchone():
        print("Error: order table does not exist")
        exit(1)
    
    # Check the schema of the order table
    cursor.execute("PRAGMA table_info([order])")  # Use square brackets to escape the reserved keyword
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print("Current order table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check if reference_number column exists
    if 'reference_number' not in column_names:
        print("\nAdding reference_number column to order table...")
        cursor.execute("ALTER TABLE [order] ADD COLUMN reference_number VARCHAR(50) UNIQUE")
        conn.commit()
        print("Column added successfully!")
    else:
        print("\nreference_number column already exists")
    
    print("\nSchema check completed")
    
except Exception as e:
    print(f"Error: {str(e)}")
    
finally:
    conn.close() 