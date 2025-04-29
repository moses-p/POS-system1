from app import app, db
from sqlalchemy import MetaData

def flush_cache():
    """Force SQLAlchemy to refresh its metadata cache"""
    print("Flushing SQLAlchemy metadata cache...")
    
    with app.app_context():
        try:
            # Force SQLAlchemy to refresh its metadata
            metadata = MetaData()
            metadata.reflect(bind=db.engine)
            
            # Show all tables and their columns
            print("\nCurrent database schema:")
            for table_name, table in metadata.tables.items():
                print(f"\nTable: {table_name}")
                for column in table.columns:
                    print(f"  - {column.name}: {column.type}")
            
            # Explicitly reflect the Order model
            db.Model.metadata.clear()
            db.Model.metadata.reflect(bind=db.engine)
            
            print("\nMetadata cache refreshed successfully")
            return True
        except Exception as e:
            print(f"Error refreshing metadata: {str(e)}")
            return False

if __name__ == "__main__":
    flush_cache() 