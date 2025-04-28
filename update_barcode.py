import sqlite3

try:
    # Connect to the database
    conn = sqlite3.connect('instance/pos.db')
    cursor = conn.cursor()
    
    # Get current table info
    cursor.execute("PRAGMA table_info(product)")
    columns = cursor.fetchall()
    
    # Create a temporary backup of products
    cursor.execute("CREATE TABLE IF NOT EXISTS product_backup AS SELECT * FROM product")
    
    # Drop the constraints from barcode field by recreating the table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_new (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        price FLOAT NOT NULL,
        stock FLOAT NOT NULL DEFAULT 0,
        max_stock FLOAT NOT NULL DEFAULT 0,
        reorder_point FLOAT NOT NULL DEFAULT 0,
        unit VARCHAR(10) NOT NULL DEFAULT 'pcs',
        category VARCHAR(50),
        image_url VARCHAR(200),
        barcode VARCHAR(50) UNIQUE,  /* Now explicitly UNIQUE but allowed to be NULL */
        created_at DATETIME,
        updated_at DATETIME,
        currency TEXT DEFAULT 'UGX'
    )
    """)
    
    # Copy data from original table
    cursor.execute("INSERT INTO product_new SELECT * FROM product")
    
    # Swap the tables
    cursor.execute("DROP TABLE product")
    cursor.execute("ALTER TABLE product_new RENAME TO product")
    
    # Commit changes and check if successful
    conn.commit()
    print("Database updated successfully!")
    
    # Check if barcode is indeed nullable
    cursor.execute("PRAGMA table_info(product)")
    new_columns = cursor.fetchall()
    barcode_column = [col for col in new_columns if col[1] == 'barcode'][0]
    print(f"Barcode column info: {barcode_column}")
    
    # If not needed anymore, drop the backup
    cursor.execute("DROP TABLE IF EXISTS product_backup")
    conn.commit()
    
    # Close the connection
    conn.close()
    
except Exception as e:
    print(f"Error updating database: {e}") 