import os
import sqlite3
import logging
from app import app, db, User, init_db
from validate_db import validate_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("pos_startup.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def ensure_db_directory():
    """Make sure the instance directory exists"""
    if not os.path.exists('instance'):
        logger.info("Creating instance directory")
        os.makedirs('instance')

def check_db_exists():
    """Check if the database file exists"""
    return os.path.exists('instance/pos.db')

def check_tables_exist():
    """Check if all required tables exist in the database"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check for essential tables
        required_tables = ['user', 'product', 'order', 'order_item', 'stock_movement', 'cart', 'cart_item']
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        conn.close()
        
        return len(missing_tables) == 0, missing_tables
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        return False, required_tables

def check_admin_exists():
    """Check if the admin user exists"""
    try:
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            return admin is not None
    except Exception as e:
        logger.error(f"Error checking admin user: {str(e)}")
        return False

def fix_order_table():
    """Fix the order table with the viewed/viewed_at columns"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check if the columns exist
        cursor.execute("PRAGMA table_info('order')")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add columns if missing
        if 'viewed' not in columns:
            logger.info("Adding 'viewed' column to order table")
            cursor.execute("ALTER TABLE \"order\" ADD COLUMN viewed BOOLEAN DEFAULT 0")
        
        if 'viewed_at' not in columns:
            logger.info("Adding 'viewed_at' column to order table")
            cursor.execute("ALTER TABLE \"order\" ADD COLUMN viewed_at TIMESTAMP")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error fixing order table: {str(e)}")
        return False

def run_checks():
    """Run all database checks and fixes"""
    logger.info("Starting database checks")
    
    # Ensure directory exists
    ensure_db_directory()
    
    # Check if database exists
    if not check_db_exists():
        logger.info("Database does not exist, initializing...")
        init_db()
        logger.info("Database initialized successfully")
        return
    
    # Check if tables exist
    tables_exist, missing_tables = check_tables_exist()
    if not tables_exist:
        logger.warning(f"Missing tables: {missing_tables}")
        logger.info("Recreating database tables")
        init_db()
    
    # Check if admin exists
    if not check_admin_exists():
        logger.warning("Admin user does not exist")
        logger.info("Creating admin user")
        with app.app_context():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    # Fix order table
    if not fix_order_table():
        logger.error("Failed to fix order table")
    
    # Run validation and fixing processes
    try:
        logger.info("Running database validation and fixes")
        validate_database()
    except Exception as e:
        logger.error(f"Error during database validation: {str(e)}")
    
    logger.info("Database checks completed")

if __name__ == "__main__":
    run_checks() 