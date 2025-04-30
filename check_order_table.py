import sqlite3

# Connect to database
conn = sqlite3.connect('instance/pos.db')
cursor = conn.cursor()

# Check order table structure
print("Checking order table structure...")
cursor.execute("PRAGMA table_info('order')")
columns = cursor.fetchall()

print("\nOrder table columns:")
for col in columns:
    print(f"Column {col[0]}: {col[1]} (Type: {col[2]}, NotNull: {col[3]}, DefaultValue: {col[4]}, PK: {col[5]})")

# Check if any orders exist
cursor.execute("SELECT COUNT(*) FROM 'order'")
count = cursor.fetchone()[0]
print(f"\nNumber of orders in database: {count}")

if count > 0:
    # Check a sample order
    cursor.execute("SELECT * FROM 'order' LIMIT 1")
    sample_order = cursor.fetchone()
    
    # Get column names
    cursor.execute("PRAGMA table_info('order')")
    column_names = [col[1] for col in cursor.fetchall()]
    
    print("\nSample order:")
    for i, value in enumerate(sample_order):
        if i < len(column_names):
            print(f"{column_names[i]}: {value}")
        else:
            print(f"Unknown column {i}: {value}")

conn.close() 