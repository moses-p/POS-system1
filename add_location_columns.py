from app import app, db
from sqlalchemy import text

def add_location_columns():
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Check if columns exist
                result = conn.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                # Add missing columns
                if 'latitude' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN latitude FLOAT"))
                    print("Added latitude column")
                if 'longitude' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN longitude FLOAT"))
                    print("Added longitude column")
                if 'location_name' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN location_name VARCHAR(200)"))
                    print("Added location_name column")
                if 'last_location_update' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN last_location_update DATETIME"))
                    print("Added last_location_update column")
                
                conn.commit()
                print("Successfully added all location columns")
        except Exception as e:
            print(f"Error adding location columns: {e}")

if __name__ == "__main__":
    add_location_columns() 