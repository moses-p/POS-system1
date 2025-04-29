import sqlite3
import os

# Make sure we're in the correct directory
db_path = 'instance/pos.db'

# Connect to the database
print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Add viewed column if it doesn't exist
    print("Checking for 'viewed' column...")
    cursor.execute("PRAGMA table_info('order')")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'viewed' not in column_names:
        print("Adding 'viewed' column...")
        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed BOOLEAN DEFAULT 0')
        print("'viewed' column added successfully.")
    else:
        print("'viewed' column already exists.")
    
    # Add viewed_at column if it doesn't exist
    if 'viewed_at' not in column_names:
        print("Adding 'viewed_at' column...")
        cursor.execute('ALTER TABLE "order" ADD COLUMN viewed_at TIMESTAMP')
        print("'viewed_at' column added successfully.")
    else:
        print("'viewed_at' column already exists.")
    
    # Commit changes
    conn.commit()
    print("Database schema updated successfully!")
    
except Exception as e:
    print(f"Error updating database: {str(e)}")
    conn.rollback()
finally:
    # Close connection
    conn.close()
    print("Database connection closed.") 