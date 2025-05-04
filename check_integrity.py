from app import app, check_db_integrity

with app.app_context():
    result = check_db_integrity()
    print(f"Database integrity check result: {result}") 