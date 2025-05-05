import sqlite3
import os

def fix_database():
    # Connect to the database
    db_path = 'pos.db'
    print(f"Connecting to database at: {os.path.abspath(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info('order')")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'reference_number' not in columns:
            print("Adding reference_number column to order table...")
            cursor.execute('ALTER TABLE "order" ADD COLUMN reference_number TEXT')
            conn.commit()
            print("Successfully added reference_number column!")
        else:
            print("reference_number column already exists!")
            
        # Verify the change
        cursor.execute("PRAGMA table_info('order')")
        print("\nCurrent order table columns:")
        for column in cursor.fetchall():
            print(f"- {column[1]} ({column[2]})")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_database() 