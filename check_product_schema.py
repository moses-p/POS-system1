import sqlite3
import os

def check_product_schema():
    """Check the schema of the product table"""
    print("Checking product table schema...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the product table schema
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        
        print("Product table columns:")
        for col in columns:
            # Column structure: (cid, name, type, notnull, dflt_value, pk)
            print(f"Column: {col[1]}, Type: {col[2]}, Not Null: {col[3]}, Default: {col[4]}, Primary Key: {col[5]}")
        
        # Get a sample product to see actual data
        cursor.execute("SELECT * FROM product LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print("\nSample product:")
            for i, col in enumerate(columns):
                print(f"{col[1]}: {sample[i]}")
        else:
            print("\nNo products found in database.")
        
        conn.close()
    except Exception as e:
        print(f"Error checking product schema: {str(e)}")

if __name__ == "__main__":
    check_product_schema() 