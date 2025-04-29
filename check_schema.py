import sqlite3
import os

print("Checking database schema...")

db_path = 'instance/pos.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check 'order' table columns
print("\nChecking 'order' table schema:")
cursor.execute("PRAGMA table_info('order')")
columns = cursor.fetchall()
for col in columns:
    print(f"Column: {col}")

print("\nChecking for 'viewed' column:")
column_names = [col[1] for col in columns]
print(f"Has 'viewed' column: {'viewed' in column_names}")
print(f"Has 'viewed_at' column: {'viewed_at' in column_names}")

# Check all tables
print("\nAll tables in database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"Table: {table[0]}")

conn.close()
print("\nSchema check complete.") 