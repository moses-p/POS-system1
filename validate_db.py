import sqlite3
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("db_validation.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the database before making changes"""
    try:
        import shutil
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

def fix_orphaned_records():
    """Fix orphaned records in the database"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Fix order items without valid orders
        cursor.execute("""
            DELETE FROM order_item 
            WHERE order_id NOT IN (SELECT id FROM "order")
        """)
        deleted_items = cursor.rowcount
        logger.info(f"Deleted {deleted_items} orphaned order items")
        
        # Fix cart items without valid carts
        cursor.execute("""
            DELETE FROM cart_item 
            WHERE cart_id NOT IN (SELECT id FROM cart)
        """)
        deleted_cart_items = cursor.rowcount
        logger.info(f"Deleted {deleted_cart_items} orphaned cart items")
        
        # Fix stock movements without valid products
        cursor.execute("""
            DELETE FROM stock_movement 
            WHERE product_id NOT IN (SELECT id FROM product)
        """)
        deleted_movements = cursor.rowcount
        logger.info(f"Deleted {deleted_movements} orphaned stock movements")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error fixing orphaned records: {str(e)}")
        return False

def reset_inventory_counts():
    """Reset inventory counts based on stock movements"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Get all products
        cursor.execute("SELECT id FROM product")
        products = cursor.fetchall()
        
        updated_products = 0
        for product_id in products:
            product_id = product_id[0]
            
            # Calculate correct stock based on movements
            cursor.execute("""
                SELECT COALESCE(
                    (SELECT SUM(CASE 
                        WHEN movement_type = 'restock' THEN quantity 
                        WHEN movement_type = 'sale' THEN -quantity 
                        ELSE 0 
                    END) FROM stock_movement WHERE product_id = ?), 
                0)
            """, (product_id,))
            
            calculated_stock = cursor.fetchone()[0]
            
            # Update product stock
            cursor.execute("""
                UPDATE product SET stock = ? WHERE id = ?
            """, (calculated_stock, product_id))
            
            if cursor.rowcount > 0:
                updated_products += 1
        
        conn.commit()
        conn.close()
        logger.info(f"Updated inventory counts for {updated_products} products")
        return True
    except Exception as e:
        logger.error(f"Error resetting inventory counts: {str(e)}")
        return False

def add_missing_indexes():
    """Add any missing indexes to improve performance"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Add indexes for common queries
        indexes = [
            ("CREATE INDEX IF NOT EXISTS idx_product_name ON product (name)", "product name"),
            ("CREATE INDEX IF NOT EXISTS idx_product_category ON product (category)", "product category"),
            ("CREATE INDEX IF NOT EXISTS idx_product_barcode ON product (barcode)", "product barcode"),
            ("CREATE INDEX IF NOT EXISTS idx_order_date ON \"order\" (order_date)", "order date"),
            ("CREATE INDEX IF NOT EXISTS idx_order_status ON \"order\" (status)", "order status"),
            ("CREATE INDEX IF NOT EXISTS idx_order_customer ON \"order\" (customer_id)", "order customer"),
            ("CREATE INDEX IF NOT EXISTS idx_order_viewed ON \"order\" (viewed)", "order viewed status"),
            ("CREATE INDEX IF NOT EXISTS idx_stock_movement_product ON stock_movement (product_id)", "stock movement product"),
            ("CREATE INDEX IF NOT EXISTS idx_cart_user ON cart (user_id)", "cart user"),
            ("CREATE INDEX IF NOT EXISTS idx_order_item_product ON order_item (product_id)", "order item product"),
            ("CREATE INDEX IF NOT EXISTS idx_order_item_order ON order_item (order_id)", "order item order"),
        ]
        
        for index_sql, index_name in indexes:
            try:
                cursor.execute(index_sql)
                logger.info(f"Created or verified index for {index_name}")
            except Exception as e:
                logger.warning(f"Error creating index for {index_name}: {str(e)}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding indexes: {str(e)}")
        return False

def check_user_roles():
    """Ensure there is at least one admin user"""
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Check for admin users
        cursor.execute("SELECT COUNT(*) FROM user WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # Create default admin if none exists
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('admin123')
            
            cursor.execute("""
                INSERT INTO user (username, email, password_hash, is_admin, is_staff)
                VALUES (?, ?, ?, ?, ?)
            """, ('admin', 'admin@example.com', password_hash, 1, 1))
            
            logger.warning("No admin users found, created default admin account")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking user roles: {str(e)}")
        return False

def validate_database():
    """Run all database validation and fixing functions"""
    logger.info("Starting database validation")
    
    # Back up the database first
    backup_database()
    
    # Fix common issues
    fix_orphaned_records()
    reset_inventory_counts()
    add_missing_indexes()
    check_user_roles()
    
    logger.info("Database validation and fixes completed")

if __name__ == "__main__":
    validate_database() 