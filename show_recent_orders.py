import sqlite3

conn = sqlite3.connect('C:/Users/Genius/Documents/POS-system1/instance/pos.db')
cursor = conn.cursor()

print(f"{'ID':<5} {'Customer Name':<25} {'Created By ID':<15} {'Order Date'}")
print('-' * 70)
for row in cursor.execute("SELECT id, customer_name, created_by_id, order_date FROM 'order' ORDER BY id ASC;"):
    print(f"{row[0]:<5} {str(row[1]):<25} {str(row[2]):<15} {row[3]}")

conn.close() 