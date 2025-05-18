import sqlite3

def add_low_stock_threshold_column(db_path='instance/pos.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info('product')")
    columns = [row[1] for row in cursor.fetchall()]
    if 'low_stock_threshold' not in columns:
        print("Adding low_stock_threshold column to product table...")
        cursor.execute("ALTER TABLE product ADD COLUMN low_stock_threshold FLOAT DEFAULT 5.0")
        conn.commit()
        print("Column added.")
    else:
        print("low_stock_threshold column already exists.")
    conn.close()

if __name__ == "__main__":
    add_low_stock_threshold_column() 