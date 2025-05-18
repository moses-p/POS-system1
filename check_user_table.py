import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('instance/pos.db')
cursor = conn.cursor()

# Check if the user table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
if cursor.fetchone() is None:
    print("The user table does not exist.")
else:
    # Get the schema of the user table
    cursor.execute("PRAGMA table_info(user)")
    columns = cursor.fetchall()
    # Print the columns
    print("Columns in user table:")
    for col in columns:
        print(col)

# Close the connection
conn.close() 