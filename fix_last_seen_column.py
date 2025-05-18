import sqlite3

DB_PATH = 'instance/pos.db'
COLUMN_NAME = 'last_seen'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if the column exists
cursor.execute("PRAGMA table_info(user);")
columns = [row[1] for row in cursor.fetchall()]

if COLUMN_NAME in columns:
    print(f"Column '{COLUMN_NAME}' already exists in 'user' table.")
else:
    print(f"Column '{COLUMN_NAME}' not found. Adding it...")
    cursor.execute(f"ALTER TABLE user ADD COLUMN {COLUMN_NAME} DATETIME;")
    conn.commit()
    print(f"Column '{COLUMN_NAME}' added successfully.")

conn.close() 