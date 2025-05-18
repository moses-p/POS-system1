import sqlite3

conn = sqlite3.connect('C:/Users/Genius/Documents/POS-system1/instance/pos.db')
cursor = conn.cursor()

print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Full Name':<25} {'Initials':<10}")
print('-' * 100)
for row in cursor.execute("SELECT id, username, email, full_name, initials FROM user ORDER BY id ASC;"):
    print(f"{row[0]:<5} {row[1]:<20} {row[2]:<30} {row[3]:<25} {row[4]:<10}")

conn.close() 