from app import app, db
from flask_migrate import upgrade, migrate, init, stamp

def run_migration():
    with app.app_context():
        try:
            # Try to run the upgrade
            print("Upgrading database schema...")
            upgrade()
        except Exception as e:
            print(f"Error upgrading: {str(e)}")
            print("Trying to initialize migration...")
            init()
            print("Creating migration for current models...")
            migrate()
            print("Stamping database as current...")
            stamp()
            print("Now trying upgrade again...")
            upgrade()
        print("Database migration complete!")

if __name__ == "__main__":
    run_migration() 