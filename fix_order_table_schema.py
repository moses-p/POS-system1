import sqlite3

def add_missing_order_columns(db_path='instance/pos.db'):
    columns_needed = [
        ('reference_number', 'VARCHAR(50)'),
        ('customer_id', 'INTEGER'),
        ('order_date', 'DATETIME'),
        ('total_amount', 'FLOAT'),
        ('status', 'VARCHAR(20)'),
        ('customer_name', 'VARCHAR(100)'),
        ('customer_phone', 'VARCHAR(20)'),
        ('customer_email', 'VARCHAR(100)'),
        ('customer_address', 'TEXT'),
        ('order_type', 'VARCHAR(20)'),
        ('created_by_id', 'INTEGER'),
        ('updated_at', 'DATETIME'),
        ('completed_at', 'DATETIME'),
        ('viewed', 'BOOLEAN'),
        ('viewed_at', 'DATETIME'),
        ('payment_status', 'VARCHAR(20)'),
        ('payment_method', 'VARCHAR(20)')
    ]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info('order')")
    columns = [row[1] for row in cursor.fetchall()]
    for col, col_type in columns_needed:
        if col not in columns:
            print(f"Adding {col} column to order table...")
            cursor.execute(f"ALTER TABLE 'order' ADD COLUMN {col} {col_type}")
            conn.commit()
            print(f"Column {col} added.")
        else:
            print(f"{col} column already exists.")
    conn.close()

if __name__ == "__main__":
    add_missing_order_columns() 