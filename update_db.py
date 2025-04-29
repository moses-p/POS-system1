import sqlite3
from app import app, db, User

def update_schema():
    print("Updating database schema...")
    
    # First, try with SQLAlchemy through Flask app context
    try:
        with app.app_context():
            # Try to access the new column to see if it exists
            try:
                User.query.filter_by(is_staff=True).first()
                print("Schema is already up to date (is_staff column exists).")
            except Exception as e:
                print(f"Adding is_staff column: {e}")
                # Use SQLite to add the column
                db.session.execute('ALTER TABLE user ADD COLUMN is_staff BOOLEAN DEFAULT FALSE')
                db.session.commit()
                print("Schema updated successfully - added is_staff column.")
    except Exception as e:
        print(f"Error with SQLAlchemy update: {e}")
        
        # Fall back to direct SQLite
        try:
            # Connect to the database
            conn = sqlite3.connect('instance/pos.db')
            cursor = conn.cursor()
            
            # Check if is_staff column already exists
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'is_staff' not in column_names:
                # Add the is_staff column
                cursor.execute('ALTER TABLE user ADD COLUMN is_staff BOOLEAN DEFAULT 0')
                conn.commit()
                print("is_staff column added successfully using direct SQLite!")
            else:
                print("is_staff column already exists")
            
            # Close the connection
            conn.close()
        except Exception as e:
            print(f"Error with direct SQLite update: {e}")
    
    print("Database update complete.")

def update_db():
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info('order')")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        print("Current columns:", column_names)
        
        # Add viewed column if it doesn't exist
        if 'viewed' not in column_names:
            print("Adding 'viewed' column...")
            cursor.execute('ALTER TABLE "order" ADD COLUMN viewed BOOLEAN DEFAULT 0')
            
        # Add viewed_at column if it doesn't exist
        if 'viewed_at' not in column_names:
            print("Adding 'viewed_at' column...")
            cursor.execute('ALTER TABLE "order" ADD COLUMN viewed_at TIMESTAMP')
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print('Database schema updated successfully.')
    except Exception as e:
        print(f'Error updating database: {str(e)}')

if __name__ == '__main__':
    update_schema()
    update_db() 