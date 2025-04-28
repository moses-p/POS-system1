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

if __name__ == '__main__':
    update_schema() 