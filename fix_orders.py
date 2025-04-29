import sqlite3
import os
from datetime import datetime

# Connect to the database
db_path = 'instance/pos.db'
print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Get count of orders
    cursor.execute('SELECT COUNT(*) FROM "order"')
    count = cursor.fetchone()[0]
    print(f"Found {count} orders in database.")
    
    # Update all existing orders to set viewed = 1 (true) to avoid alarms for old orders
    print("Setting all existing orders as viewed...")
    cursor.execute('UPDATE "order" SET viewed = 1, viewed_at = ? WHERE viewed IS NULL', (datetime.now().isoformat(),))
    updated = cursor.rowcount
    print(f"Updated {updated} orders with viewed status.")
    
    # Commit changes
    conn.commit()
    print("Orders updated successfully!")
    
    # Check if columns exist with proper data
    print("Verifying columns in Order table:")
    cursor.execute('PRAGMA table_info("order")')
    columns = cursor.fetchall()
    for col in columns:
        # col[1] is the column name
        if col[1] in ['viewed', 'viewed_at']:
            print(f"  - {col[1]}: {col[2]} (Default: {col[4]})")
    
    # Check for pending orders
    cursor.execute('SELECT COUNT(*) FROM "order" WHERE viewed = 0')
    pending = cursor.fetchone()[0]
    print(f"Orders waiting to be viewed: {pending}")
    
except Exception as e:
    print(f"Error updating orders: {str(e)}")
    conn.rollback()
finally:
    # Close connection
    conn.close()
    print("Database connection closed.") 