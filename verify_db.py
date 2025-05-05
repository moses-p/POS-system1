import sqlite3
import os

def verify_database():
    print("Verifying database connection and structure...")
    
    # Check if database file exists
    db_path = 'instance/pos.db'
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:", tables)
        
        # Check product table structure
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        print("\nProduct table columns:", columns)
        
        # Check for data
        cursor.execute("SELECT COUNT(*) FROM product")
        count = cursor.fetchone()[0]
        print(f"\nNumber of products: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM product LIMIT 1")
            sample = cursor.fetchone()
            print("\nSample product:", sample)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = verify_database()
    if not success:
        print("\nDatabase verification failed!")
    else:
        print("\nDatabase verification successful!") 