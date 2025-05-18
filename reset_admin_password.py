import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = 'instance/pos.db'
NEW_PASSWORD = 'admin123'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

password_hash = generate_password_hash(NEW_PASSWORD)
cursor.execute("UPDATE user SET password_hash = ? WHERE username = 'admin'", (password_hash,))
conn.commit()
conn.close()

print('Admin password has been reset to admin123 in instance/pos.db.') 