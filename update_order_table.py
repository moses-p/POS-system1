from app import app, db
import sqlite3

def add_columns_to_order_table():
    print("Adding columns to Order table...")
    
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(order)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Add updated_at column if it doesn't exist
        if 'updated_at' not in column_names:
            cursor.execute('ALTER TABLE "order" ADD COLUMN updated_at TIMESTAMP')
            print("Added updated_at column")
        else:
            print("updated_at column already exists")
            
        # Add completed_at column if it doesn't exist
        if 'completed_at' not in column_names:
            cursor.execute('ALTER TABLE "order" ADD COLUMN completed_at TIMESTAMP')
            print("Added completed_at column")
        else:
            print("completed_at column already exists")
        
        # Commit changes
        conn.commit()
        conn.close()
        print("Database update complete.")
        
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    add_columns_to_order_table() 