import sqlite3
import datetime

# Connect to the database
conn = sqlite3.connect('instance/pos.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Automatic Stock Repair Tool ===")
print("This script will automatically fix stock values based on stock movements")

# Get all products
cursor.execute("SELECT id, name, stock FROM product ORDER BY id")
products = cursor.fetchall()

fixed_count = 0
total_products = len(products)

for product in products:
    product_id = product['id']
    current_stock = product['stock']
    
    # Calculate what the stock should be based on stock movements
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN movement_type = 'restock' THEN quantity ELSE 0 END) as total_restocked,
        SUM(CASE WHEN movement_type = 'sale' THEN quantity ELSE 0 END) as total_sold
    FROM stock_movement 
    WHERE product_id = ?
    """, (product_id,))
    
    result = cursor.fetchone()
    total_restocked = result['total_restocked'] or 0
    total_sold = result['total_sold'] or 0
    
    calculated_stock = total_restocked - total_sold
    
    print(f"Product: {product['name']} (ID: {product_id})")
    print(f"  Current stock in DB: {current_stock}")
    print(f"  Calculated from movements: {calculated_stock} (Restocked: {total_restocked}, Sold: {total_sold})")
    
    if abs(current_stock - calculated_stock) > 0.001:  # Allow for float rounding errors
        print(f"  Discrepancy detected: {current_stock - calculated_stock}")
        
        # Update the stock in the database
        cursor.execute("UPDATE product SET stock = ?, updated_at = ? WHERE id = ?", 
                        (calculated_stock, datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), product_id))
        
        # Create a stock movement record to document the fix
        cursor.execute("""
        INSERT INTO stock_movement 
        (product_id, quantity, movement_type, remaining_stock, timestamp, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            abs(calculated_stock - current_stock),
            'restock' if calculated_stock > current_stock else 'sale',
            calculated_stock,
            datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
            f"Stock correction: Auto-fixed discrepancy between DB stock ({current_stock}) and calculated stock ({calculated_stock})"
        ))
        
        conn.commit()
        print(f"  Stock updated to {calculated_stock}")
        fixed_count += 1
    else:
        print("  Stock is correct")
    
    # Force update timestamp to ensure UI refreshes
    cursor.execute("UPDATE product SET updated_at = ? WHERE id = ?", 
                   (datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), product_id))
    conn.commit()
    
    print("")

print(f"\n=== Summary ===")
print(f"Total products checked: {total_products}")
print(f"Products with stock fixed: {fixed_count}")

print("\n=== Verifying fixes by recalculating stocks ===")
# Verify the fixes
cursor.execute("SELECT id, name, stock FROM product ORDER BY id")
products = cursor.fetchall()

all_correct = True
for product in products:
    product_id = product['id']
    current_stock = product['stock']
    
    # Calculate what the stock should be based on stock movements
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN movement_type = 'restock' THEN quantity ELSE 0 END) as total_restocked,
        SUM(CASE WHEN movement_type = 'sale' THEN quantity ELSE 0 END) as total_sold
    FROM stock_movement 
    WHERE product_id = ?
    """, (product_id,))
    
    result = cursor.fetchone()
    total_restocked = result['total_restocked'] or 0
    total_sold = result['total_sold'] or 0
    
    calculated_stock = total_restocked - total_sold
    
    if abs(current_stock - calculated_stock) > 0.001:  # Allow for float rounding errors
        print(f"WARNING: Product {product['name']} (ID: {product_id}) still has discrepancy!")
        print(f"  Current: {current_stock}, Calculated: {calculated_stock}")
        all_correct = False

if all_correct:
    print("All product stocks now match their stock movement records!")

print("\n=== Checking for database consistency ===")
# Check for integrity constraints
cursor.execute("PRAGMA foreign_key_check")
fk_violations = cursor.fetchall()
if fk_violations:
    print(f"Foreign key violations found: {fk_violations}")
else:
    print("No foreign key violations found")

# Check for orphaned stock movements
cursor.execute("""
SELECT COUNT(*) FROM stock_movement sm 
LEFT JOIN product p ON sm.product_id = p.id
WHERE p.id IS NULL
""")
orphaned = cursor.fetchone()[0]
if orphaned > 0:
    print(f"Found {orphaned} orphaned stock movement records")
else:
    print("No orphaned stock movement records found")

conn.close()
print("\nDatabase repair complete") 