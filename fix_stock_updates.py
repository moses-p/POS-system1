import sqlite3
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_fixes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_stock_consistency():
    """
    Check if product stock values match the actual stock movements history.
    Identifies any inconsistencies in the stock values.
    """
    logger.info("Checking stock consistency between product table and stock movements...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all products
        cursor.execute("SELECT id, name, stock FROM product ORDER BY id")
        products = cursor.fetchall()
        
        inconsistencies = []
        
        for product_id, product_name, current_stock in products:
            # Calculate expected stock based on stock movements
            cursor.execute("""
                SELECT 
                    COALESCE(
                        (SELECT SUM(CASE 
                            WHEN movement_type = 'restock' THEN quantity 
                            WHEN movement_type = 'sale' THEN -quantity 
                            ELSE 0 
                        END) FROM stock_movement WHERE product_id = ?), 
                        0
                    ) as calculated_stock
            """, (product_id,))
            
            calculated_stock = cursor.fetchone()[0]
            
            # Compare with current stock value
            if calculated_stock is not None and abs(float(calculated_stock) - float(current_stock)) > 0.0001:
                inconsistencies.append({
                    'product_id': product_id,
                    'product_name': product_name,
                    'current_stock': current_stock,
                    'calculated_stock': calculated_stock,
                    'difference': float(current_stock) - float(calculated_stock)
                })
        
        # Report findings
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} products with stock inconsistencies:")
            for item in inconsistencies:
                logger.warning(f"Product ID {item['product_id']} ({item['product_name']}): " 
                             f"Current: {item['current_stock']}, Calculated: {item['calculated_stock']}, "
                             f"Difference: {item['difference']}")
        else:
            logger.info("All product stock values are consistent with stock movements.")
        
        return inconsistencies
    
    except Exception as e:
        logger.error(f"Error checking stock consistency: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def check_stock_movement_timestamps():
    """
    Check if there are any stock movements with timestamp issues.
    """
    logger.info("Checking stock movement timestamps...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for NULL timestamps
        cursor.execute("SELECT COUNT(*) FROM stock_movement WHERE timestamp IS NULL")
        null_timestamps = cursor.fetchone()[0]
        
        if null_timestamps > 0:
            logger.warning(f"Found {null_timestamps} stock movements with NULL timestamps")
        else:
            logger.info("No stock movements with NULL timestamps found")
        
        # Check for stock movements in the future
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(f"SELECT COUNT(*) FROM stock_movement WHERE timestamp > ?", (now,))
        future_timestamps = cursor.fetchone()[0]
        
        if future_timestamps > 0:
            logger.warning(f"Found {future_timestamps} stock movements with future timestamps")
        else:
            logger.info("No stock movements with future timestamps found")
        
        return {
            'null_timestamps': null_timestamps,
            'future_timestamps': future_timestamps
        }
    
    except Exception as e:
        logger.error(f"Error checking stock movement timestamps: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def fix_stock_based_on_movements():
    """
    Fix product stock values based on stock movement history.
    """
    logger.info("Fixing product stock values based on stock movement history...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, check for inconsistencies
        inconsistencies = check_stock_consistency()
        
        if not inconsistencies:
            logger.info("No inconsistencies found, no fix needed")
            return
        
        fixed_count = 0
        
        # Fix each inconsistent product
        for item in inconsistencies:
            product_id = item['product_id']
            calculated_stock = item['calculated_stock']
            
            # Update the product stock value
            cursor.execute("""
                UPDATE product 
                SET stock = ?, updated_at = ? 
                WHERE id = ?
            """, (calculated_stock, datetime.now().isoformat(), product_id))
            
            fixed_count += 1
        
        conn.commit()
        logger.info(f"Fixed stock values for {fixed_count} products")
        
        # Verify fix was successful
        inconsistencies_after = check_stock_consistency()
        if not inconsistencies_after:
            logger.info("Stock consistency verification successful")
        else:
            logger.warning(f"There are still {len(inconsistencies_after)} inconsistencies after fix")
        
        return fixed_count
    
    except Exception as e:
        logger.error(f"Error fixing stock values: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def fix_ui_refresh_issue():
    """
    Add cache prevention headers to stock status API response.
    This fixes the issue where the UI may not reflect the latest stock values.
    """
    logger.info("Checking caching-related code in app.py for stock status API...")
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        logger.error(f"App file not found: {app_file}")
        return False
    
    # Create a backup of the app.py file
    backup_file = f'app.py.stock_fix_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    try:
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created backup of app.py: {backup_file}")
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return False
    
    # Check if the stock status API already has no-cache headers
    stock_api_pattern = '@app.route(\'/api/stock_status\')'
    if stock_api_pattern in content:
        response_pattern = 'return jsonify(result)'
        
        # Add cache prevention headers if not already present
        if 'response.headers[\'Cache-Control\']' not in content:
            modified_content = content.replace(
                'return jsonify(result)',
                'response = jsonify(result)\n'
                '            response.headers[\'Cache-Control\'] = \'no-cache, no-store, must-revalidate\'\n'
                '            response.headers[\'Pragma\'] = \'no-cache\'\n'
                '            response.headers[\'Expires\'] = \'0\'\n'
                '            return response'
            )
            
            # Save the modified content
            try:
                with open(app_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                logger.info("Added cache prevention headers to stock status API")
                return True
            except Exception as e:
                logger.error(f"Error updating app.py: {str(e)}")
                return False
        else:
            logger.info("Cache prevention headers already present in stock status API")
            return True
    else:
        logger.error("Could not find stock status API endpoint in app.py")
        return False

def fix_stock_update_commit():
    """
    Check if the product.update_stock method is properly committing changes
    """
    logger.info("Checking if stock updates are properly committed...")
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        logger.error(f"App file not found: {app_file}")
        return False
    
    # Create a backup if not already created
    backup_file = f'app.py.stock_fix_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    if not os.path.exists(backup_file):
        try:
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Created backup of app.py: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False
    
    # Check if we already have explicit db.session.commit() calls in update_stock
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def update_stock' in content and 'db.session.commit()' in content:
        # We have an explicit commit, it should be good
        logger.info("Stock update method has explicit commit")
        return True
    else:
        logger.warning("Stock update method may not have explicit commit, this could cause inconsistencies")
        return False

def main():
    """Main function to run all stock fix operations"""
    logger.info("Starting stock fix operations...")
    
    # First, check for inconsistencies
    inconsistencies = check_stock_consistency()
    
    # Check timestamp issues
    timestamp_issues = check_stock_movement_timestamps()
    
    # Fix UI refresh issues
    ui_fix_result = fix_ui_refresh_issue()
    
    # Check if stock updates are properly committed
    commit_check = fix_stock_update_commit()
    
    # Fix stock inconsistencies if needed
    if inconsistencies:
        fixed_count = fix_stock_based_on_movements()
        logger.info(f"Fixed {fixed_count} products with stock inconsistencies")
    
    logger.info("Stock fix operations completed")

if __name__ == "__main__":
    main() 