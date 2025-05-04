import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('instance/pos.db')
c = conn.cursor()

# Prepare data for a test sale
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
total_amount = 12345.67
status = 'completed'

# Insert the test sale
c.execute("INSERT INTO 'order' (order_date, total_amount, status) VALUES (?, ?, ?)", (now, total_amount, status))
conn.commit()
conn.close()
print('Test sale added for today.') 