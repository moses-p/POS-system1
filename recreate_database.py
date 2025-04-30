import sqlite3
import os
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("database_recreation.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the current database"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = 'instance/pos.db'
        target = f'instance/pos_backup_{timestamp}.db'
        
        if os.path.exists(source):
            shutil.copy2(source, target)
            logger.info(f"Database backed up to {target}")
            return True
        else:
            logger.warning("Database file not found, no backup created")
            return False
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def recreate_database():
    """Completely recreate the database with correct schema"""
    try:
        # First, backup the existing database
        backup_database()
        
        # Database path
        db_path = 'instance/pos.db'
        
        # Remove existing database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Removed existing database at {db_path}")
        
        # Ensure instance directory exists
        os.makedirs('instance', exist_ok=True)
        
        # Create new database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create user table
        logger.info("Creating user table")
        cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(128),
            is_admin BOOLEAN DEFAULT 0,
            is_staff BOOLEAN DEFAULT 0
        )
        ''')
        
        # Create product table
        logger.info("Creating product table")
        cursor.execute('''
        CREATE TABLE product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price FLOAT NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'UGX',
            stock FLOAT NOT NULL DEFAULT 0,
            max_stock FLOAT NOT NULL DEFAULT 0,
            reorder_point FLOAT NOT NULL DEFAULT 0,
            unit VARCHAR(10) NOT NULL DEFAULT 'pcs',
            category VARCHAR(50),
            image_url VARCHAR(200),
            barcode VARCHAR(50) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create order table with clear schema
        logger.info("Creating order table")
        cursor.execute('''
        CREATE TABLE "order" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_number VARCHAR(50) UNIQUE,
            customer_id INTEGER,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount FLOAT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            customer_name VARCHAR(100),
            customer_phone VARCHAR(20),
            customer_email VARCHAR(100),
            customer_address TEXT,
            order_type VARCHAR(20) DEFAULT 'online',
            created_by_id INTEGER,
            updated_at TIMESTAMP,
            completed_at TIMESTAMP,
            viewed BOOLEAN DEFAULT 0,
            viewed_at TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES user(id),
            FOREIGN KEY (created_by_id) REFERENCES user(id)
        )
        ''')
        
        # Create order_item table
        logger.info("Creating order_item table")
        cursor.execute('''
        CREATE TABLE order_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price FLOAT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES "order"(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
        ''')
        
        # Create stock_movement table
        logger.info("Creating stock_movement table")
        cursor.execute('''
        CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity FLOAT NOT NULL,
            movement_type VARCHAR(20) NOT NULL,
            remaining_stock FLOAT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
        ''')
        
        # Create price_change table
        logger.info("Creating price_change table")
        cursor.execute('''
        CREATE TABLE price_change (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price FLOAT NOT NULL,
            new_price FLOAT NOT NULL,
            changed_by_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES product(id),
            FOREIGN KEY (changed_by_id) REFERENCES user(id)
        )
        ''')
        
        # Create cart and cart_item tables
        logger.info("Creating cart and cart_item tables")
        cursor.execute('''
        CREATE TABLE cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status VARCHAR(20) DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE cart_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (cart_id) REFERENCES cart(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
        ''')
        
        # Create indexes for better performance
        logger.info("Creating indexes")
        cursor.execute("CREATE INDEX idx_product_category ON product(category)")
        cursor.execute("CREATE INDEX idx_product_name ON product(name)")
        cursor.execute("CREATE INDEX idx_order_customer_id ON \"order\"(customer_id)")
        cursor.execute("CREATE INDEX idx_order_date ON \"order\"(order_date)")
        cursor.execute("CREATE INDEX idx_order_status ON \"order\"(status)")
        cursor.execute("CREATE UNIQUE INDEX idx_order_reference_number ON \"order\"(reference_number)")
        
        # Create a default admin user
        cursor.execute('''
        INSERT INTO user (username, email, password_hash, is_admin, is_staff)
        VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin@example.com', 
             # This is a hash for 'password' - replace with a proper hash in production
             'pbkdf2:sha256:260000$4sW1JK7JEARTm2eU$c14fbb70202a6e252e7af2af56b6c0b93c323d4ee4df7ada17a9cfce49134a61', 
             1, 1))
        
        # Commit changes and close
        conn.commit()
        conn.close()
        
        logger.info("Database recreation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error recreating database: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    recreate_database() 