from app import app, db
import sqlite3
from sqlalchemy import text
import os
import logging
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database():
    # Connect to database
    conn = sqlite3.connect('instance/pos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Examine schema
        logger.info("Examining database schema...")
        cursor.execute("PRAGMA table_info('order')")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"Order table columns: {column_names}")
        
        # Check for foreign key violations
        logger.info("Checking foreign key constraints...")
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
        if violations:
            logger.error(f"Foreign key violations found: {violations}")
            
            # Try to fix violations
            logger.info("Fixing foreign key violations...")
            for violation in violations:
                try:
                    table = violation[0]
                    rowid = violation[1]
                    ref_table = violation[2]
                    ref_index = violation[3]
                    
                    logger.info(f"Fixing violation in {table} (row {rowid}): references {ref_table}")
                    
                    # Get column name that has the foreign key
                    cursor.execute(f"PRAGMA foreign_key_list('{table}')")
                    fk_columns = cursor.fetchall()
                    fk_column = None
                    ref_column = None
                    for fk in fk_columns:
                        if fk['table'] == ref_table:
                            fk_column = fk['from']
                            ref_column = fk['to']
                            break
                    
                    if not fk_column or not ref_column:
                        logger.error(f"Could not find foreign key column for {table} -> {ref_table}")
                        continue
                    
                    # Get the row that has the violation
                    cursor.execute(f"SELECT * FROM '{table}' WHERE rowid = ?", (rowid,))
                    violating_row = cursor.fetchone()
                    if not violating_row:
                        logger.warning(f"Violating row {rowid} not found in {table}")
                        continue
                    
                    logger.info(f"Violating row: {dict(violating_row)}")
                    
                    # Check if we can fix it by setting to NULL (if nullable)
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    table_info = cursor.fetchall()
                    column_info = next((col for col in table_info if col['name'] == fk_column), None)
                    
                    if column_info and column_info['notnull'] == 0:
                        # Column is nullable, set to NULL
                        logger.info(f"Setting {table}.{fk_column} to NULL for row {rowid}")
                        cursor.execute(f"UPDATE '{table}' SET {fk_column} = NULL WHERE rowid = ?", (rowid,))
                    else:
                        # Column is not nullable, delete the row
                        logger.info(f"Deleting row {rowid} from {table} due to foreign key violation")
                        cursor.execute(f"DELETE FROM '{table}' WHERE rowid = ?", (rowid,))
                except Exception as e:
                    logger.error(f"Error fixing violation: {str(e)}")
                    traceback.print_exc()
        
        # Fix inconsistent stock
        logger.info("Checking for stock inconsistencies...")
        cursor.execute("""
        SELECT p.id, p.name, p.stock, 
            (SELECT COALESCE(SUM(quantity), 0) FROM stock_movement 
             WHERE product_id = p.id AND movement_type = 'restock') as total_restock,
            (SELECT COALESCE(SUM(quantity), 0) FROM stock_movement 
             WHERE product_id = p.id AND movement_type = 'sale') as total_sales
        FROM product p
        """)
        
        stock_discrepancies = []
        for row in cursor.fetchall():
            product_id = row['id']
            name = row['name']
            current_stock = row['stock']
            total_restock = row['total_restock'] or 0
            total_sales = row['total_sales'] or 0
            expected_stock = total_restock - total_sales
            
            if abs(current_stock - expected_stock) > 0.01:  # Small tolerance for float comparison
                stock_discrepancies.append({
                    'product_id': product_id,
                    'name': name,
                    'current_stock': current_stock,
                    'expected_stock': expected_stock,
                    'difference': current_stock - expected_stock
                })
        
        # Fix stock discrepancies
        if stock_discrepancies:
            logger.info(f"Found {len(stock_discrepancies)} stock discrepancies to fix")
            for discrepancy in stock_discrepancies:
                logger.info(f"Fixing stock for {discrepancy['name']}: current={discrepancy['current_stock']}, expected={discrepancy['expected_stock']}")
                
                # Update the product stock to match the expected value
                try:
                    cursor.execute(
                        "UPDATE product SET stock = ? WHERE id = ?", 
                        (discrepancy['expected_stock'], discrepancy['product_id'])
                    )
                    
                    # Add a stock adjustment record
                    cursor.execute("""
                    INSERT INTO stock_movement 
                    (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        discrepancy['product_id'],
                        abs(discrepancy['difference']),
                        'restock' if discrepancy['difference'] > 0 else 'sale',
                        discrepancy['expected_stock'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                        f"Automatic adjustment to correct stock discrepancy"
                    ))
                except Exception as e:
                    logger.error(f"Error fixing stock for {discrepancy['name']}: {str(e)}")
        
        # Fix duplicate records in cart_item
        logger.info("Checking for duplicate cart items...")
        cursor.execute("""
        SELECT cart_id, product_id, COUNT(*) as count
        FROM cart_item
        GROUP BY cart_id, product_id
        HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate cart items to fix")
            for duplicate in duplicates:
                cart_id = duplicate['cart_id']
                product_id = duplicate['product_id']
                count = duplicate['count']
                
                logger.info(f"Fixing duplicate cart item: cart_id={cart_id}, product_id={product_id}, count={count}")
                
                # Get all the duplicates
                cursor.execute("""
                SELECT id, quantity FROM cart_item 
                WHERE cart_id = ? AND product_id = ?
                ORDER BY id
                """, (cart_id, product_id))
                
                items = cursor.fetchall()
                if len(items) <= 1:
                    continue
                
                # Keep the first one and sum up quantities
                keep_id = items[0]['id']
                total_quantity = sum(item['quantity'] for item in items)
                
                # Update the first one with the total quantity
                cursor.execute("""
                UPDATE cart_item SET quantity = ? 
                WHERE id = ?
                """, (total_quantity, keep_id))
                
                # Delete the rest
                for item in items[1:]:
                    cursor.execute("DELETE FROM cart_item WHERE id = ?", (item['id'],))
                
                logger.info(f"Fixed duplicate cart items for cart_id={cart_id}, product_id={product_id}")
        
        # Commit all changes
        conn.commit()
        logger.info("Database fixes committed")
        
        # Verify database integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        logger.info(f"Database integrity check: {integrity}")
        
        return "Database fix complete"
    except Exception as e:
        logger.error(f"Error during database fix: {str(e)}")
        traceback.print_exc()
        conn.rollback()
        return f"Database fix failed: {str(e)}"
    finally:
        # Close connection
        conn.close()

if __name__ == "__main__":
    print(fix_database()) 