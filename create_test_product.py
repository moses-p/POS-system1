import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("test_setup.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def create_test_product():
    """
    Create a test product to allow initial system testing
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if we already have products
        cursor.execute("SELECT COUNT(*) as count FROM product")
        count = cursor.fetchone()['count']
        
        if count > 0:
            logger.info(f"Database already has {count} products, no need to create test data")
            conn.close()
            return True
        
        # Add a test product
        cursor.execute('''
        INSERT INTO product (
            name, description, price, currency, stock, 
            max_stock, reorder_point, unit, category, image_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Test Product', 
            'This is a test product for initial system setup', 
            10.0, 
            'UGX',
            100.0,
            200.0,
            20.0,
            'pcs',
            'Test',
            ''
        ))
        
        product_id = cursor.lastrowid
        
        # Add stock movement record
        cursor.execute('''
        INSERT INTO stock_movement (
            product_id, quantity, movement_type, remaining_stock, notes
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            product_id,
            100.0,
            'restock',
            100.0,
            'Initial test stock'
        ))
        
        conn.commit()
        logger.info(f"Created test product with ID {product_id}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating test product: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    create_test_product() 