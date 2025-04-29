from app import app, db
import sqlite3
from sqlalchemy import text

def fix_database():
    print("Fixing database schema with SQLAlchemy...")
    
    with app.app_context():
        try:
            # Check if the columns exist in the database
            conn = sqlite3.connect('instance/pos.db')
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info('order')")
            columns = cursor.fetchall()
            
            # Print full column details
            print("Current columns in database:")
            for col in columns:
                print(f"  {col}")
                
            column_names = [column[1] for column in columns]
            print(f"Column names: {column_names}")
            conn.close()
            
            # Force SQLAlchemy to create the columns if they don't exist
            try:
                db.session.execute(text("ALTER TABLE \"order\" ADD COLUMN viewed BOOLEAN DEFAULT 0"))
                print("Added 'viewed' column or it already exists")
            except Exception as e:
                print(f"Error adding 'viewed' column: {e}")
                
            try:
                db.session.execute(text("ALTER TABLE \"order\" ADD COLUMN viewed_at TIMESTAMP"))
                print("Added 'viewed_at' column or it already exists")
            except Exception as e:
                print(f"Error adding 'viewed_at' column: {e}")
                
            db.session.commit()
            
            # Ensure SQLAlchemy recognizes the columns by explicitly selecting them
            try:
                result = db.session.execute(text("SELECT id, viewed, viewed_at FROM \"order\" LIMIT 1")).fetchone()
                print(f"Sample order: {result}")
                
                # Check that SQLAlchemy can query the columns
                result = db.session.execute(text("SELECT COUNT(*) FROM \"order\" WHERE viewed = 0")).scalar()
                print(f"Number of unviewed orders: {result}")
                
                print("Database schema updated successfully")
                return True
            except Exception as e:
                print(f"Error testing database changes: {str(e)}")
                db.session.rollback()
                return False
                
        except Exception as e:
            print(f"Error updating database: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False

if __name__ == "__main__":
    fix_database() 