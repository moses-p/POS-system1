import sqlite3
import os
from datetime import datetime

# Connect to the database
db_path = 'instance/pos.db'
print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Get existing orders for backup
    print("Backing up existing orders...")
    cursor.execute('SELECT * FROM "order"')
    orders = cursor.fetchall()
    
    # Get column names
    cursor.execute('PRAGMA table_info("order")')
    columns_info = cursor.fetchall()
    column_names = [col[1] for col in columns_info]
    print(f"Order table has {len(column_names)} columns: {', '.join(column_names)}")
    
    # Check for specific column indices
    viewed_index = -1
    viewed_at_index = -1
    
    for i, col_name in enumerate(column_names):
        if col_name == 'viewed':
            viewed_index = i
        elif col_name == 'viewed_at':
            viewed_at_index = i
    
    print(f"viewed column index: {viewed_index}")
    print(f"viewed_at column index: {viewed_at_index}")
    
    # Update SQLite db schema - approach 1: add new columns with correct default value
    if viewed_index == -1:
        print("Adding 'viewed' column with DEFAULT 1 for all existing orders...")
        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed BOOLEAN DEFAULT 1 NOT NULL')
    
    if viewed_at_index == -1:
        print("Adding 'viewed_at' column...")
        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed_at TIMESTAMP DEFAULT NULL')
    
    # Ensure all existing records have viewed = 1
    cursor.execute('UPDATE "order" SET viewed = 1 WHERE viewed IS NULL')
    updated_records = cursor.rowcount
    print(f"Updated {updated_records} records with NULL viewed status.")
    
    # Mark some orders as unviewed for testing (adjust order_id as needed)
    cursor.execute('UPDATE "order" SET viewed = 0, viewed_at = NULL WHERE id = (SELECT MAX(id) FROM "order")')
    print(f"Marked newest order as unviewed for testing.")
    
    # Commit changes
    conn.commit()
    print("Database updated successfully!")
    
    # Verify changes
    cursor.execute('SELECT id, status, viewed, viewed_at FROM "order" ORDER BY id DESC LIMIT 5')
    results = cursor.fetchall()
    print("\nVerifying most recent orders:")
    for order in results:
        print(f"Order #{order[0]}: Status={order[1]}, Viewed={order[2]}, Viewed_at={order[3]}")
    
except Exception as e:
    print(f"Error updating database: {str(e)}")
    conn.rollback()
finally:
    # Close connection
    conn.close()
    print("\nDatabase connection closed.") 