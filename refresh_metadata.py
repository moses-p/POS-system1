from app import app, db

with app.app_context():
    # Refresh SQLAlchemy's view of the database schema
    db.Model.metadata.reflect(db.engine)
    
    # Print table names and columns to verify everything is visible
    for table_name in db.Model.metadata.tables.keys():
        print(f"Table: {table_name}")
        table = db.Model.metadata.tables[table_name]
        for column in table.columns:
            print(f"  - {column.name}: {column.type}")
    
    print("\nMetadata refresh complete. Please restart your Flask application.") 