import sqlite3
import os
from datetime import datetime
import time
import logging
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_test_product():
    """
    Create a test product to use for stock update testing
    """
    logger.info("Creating a test product for stock update testing...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if test product already exists
        cursor.execute("SELECT id FROM product WHERE name = 'Test Stock Update Product'")
        existing_product = cursor.fetchone()
        
        if existing_product:
            product_id = existing_product[0]
            logger.info(f"Test product already exists with ID: {product_id}")
            
            # Reset the stock to an initial value
            initial_stock = 50.0
            cursor.execute("""
                UPDATE product 
                SET stock = ?, updated_at = ?
                WHERE id = ?
            """, (initial_stock, datetime.now().isoformat(), product_id))
            
            # Add a restock movement
            cursor.execute("""
                INSERT INTO stock_movement 
                (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
                VALUES (?, ?, 'restock', ?, ?, 'Reset for testing')
            """, (product_id, initial_stock, initial_stock, datetime.now().isoformat()))
            
            conn.commit()
            logger.info(f"Reset test product stock to {initial_stock}")
            return product_id
        
        # Create a new test product
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO product 
            (name, description, price, stock, max_stock, reorder_point, unit, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Test Stock Update Product',
            'Product created for testing stock updates',
            1500.0,
            50.0,  # initial stock
            100.0,  # max stock
            10.0,   # reorder point
            'unit',
            'test',
            now,
            now
        ))
        
        # Get the ID of the new product
        product_id = cursor.lastrowid
        
        # Add initial stock movement
        cursor.execute("""
            INSERT INTO stock_movement 
            (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
            VALUES (?, ?, 'restock', ?, ?, 'Initial stock')
        """, (product_id, 50.0, 50.0, now))
        
        conn.commit()
        logger.info(f"Created test product with ID: {product_id}")
        return product_id
    
    except Exception as e:
        logger.error(f"Error creating test product: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def update_test_product_stock(product_id, action='both'):
    """
    Update the stock of the test product
    
    Args:
        product_id: The ID of the test product
        action: 'sale', 'restock', or 'both' (perform both operations)
    """
    logger.info(f"Updating stock for product {product_id}, action: {action}")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current stock
        cursor.execute("SELECT stock FROM product WHERE id = ?", (product_id,))
        current_stock = cursor.fetchone()[0]
        logger.info(f"Current stock: {current_stock}")
        
        # Calculate sale and restock amounts
        sale_amount = min(10.0, current_stock * 0.2)  # 20% of current stock, max 10
        restock_amount = 15.0  # fixed restock amount
        
        if action in ['sale', 'both']:
            # Perform a sale
            new_stock_after_sale = current_stock - sale_amount
            cursor.execute("""
                UPDATE product 
                SET stock = ?, updated_at = ?
                WHERE id = ?
            """, (new_stock_after_sale, datetime.now().isoformat(), product_id))
            
            # Add a sale movement
            cursor.execute("""
                INSERT INTO stock_movement 
                (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
                VALUES (?, ?, 'sale', ?, ?, 'Test sale')
            """, (product_id, sale_amount, new_stock_after_sale, datetime.now().isoformat()))
            
            logger.info(f"Performed test sale: -{sale_amount}, new stock: {new_stock_after_sale}")
            current_stock = new_stock_after_sale
        
        # Pause to allow separate DB transactions
        time.sleep(1)
        
        if action in ['restock', 'both']:
            # Perform a restock
            new_stock_after_restock = current_stock + restock_amount
            cursor.execute("""
                UPDATE product 
                SET stock = ?, updated_at = ?
                WHERE id = ?
            """, (new_stock_after_restock, datetime.now().isoformat(), product_id))
            
            # Add a restock movement
            cursor.execute("""
                INSERT INTO stock_movement 
                (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
                VALUES (?, ?, 'restock', ?, ?, 'Test restock')
            """, (product_id, restock_amount, new_stock_after_restock, datetime.now().isoformat()))
            
            logger.info(f"Performed test restock: +{restock_amount}, new stock: {new_stock_after_restock}")
        
        conn.commit()
        return True
    
    except Exception as e:
        logger.error(f"Error updating stock: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def run_stock_update_simulation():
    """
    Run a simulation of multiple stock updates to test real-time refresh
    """
    logger.info("Starting stock update simulation...")
    
    # First, create or reset the test product
    product_id = create_test_product()
    if not product_id:
        logger.error("Failed to create test product")
        return
    
    logger.info(f"Test product ID: {product_id}")
    logger.info("Starting stock update simulation. Please open your browser to view real-time updates.")
    logger.info("Product stock will be updated every 5 seconds.")
    
    try:
        for i in range(5):
            logger.info(f"Simulation round {i+1}/5")
            
            # Randomly choose between sale, restock, or both
            actions = ['sale', 'restock', 'both']
            action = random.choice(actions)
            
            # Update stock
            update_test_product_stock(product_id, action)
            
            # Wait to allow UI to refresh
            logger.info("Waiting 5 seconds before next update...")
            time.sleep(5)
        
        logger.info("Stock update simulation completed successfully.")
        logger.info(f"Test product ID: {product_id}, Name: 'Test Stock Update Product'")
        logger.info("Check if the UI reflected all these changes in real-time.")
        
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    except Exception as e:
        logger.error(f"Error during simulation: {str(e)}")

if __name__ == "__main__":
    run_stock_update_simulation() 