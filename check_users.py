import sqlite3
from datetime import datetime

def generate_initials(name):
    if not name:
        return ""
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return parts[0][0].upper()

def update_users():
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("""
            SELECT id, username, email, full_name
            FROM user
            ORDER BY id
        """)
        
        users = cursor.fetchall()
        print(f"Fetched {len(users)} users from the database.")
        
        for user in users:
            user_id = user[0]
            username = user[1]
            full_name = user[3] if user[3] else username
            initials = generate_initials(full_name)
            print(f"Updating user {username} with full_name: {full_name}, initials: {initials}")
            cursor.execute("""
                UPDATE user
                SET full_name = ?, initials = ?
                WHERE id = ?
            """, (full_name, initials, user_id))
        
        conn.commit()
        conn.close()
        print("User updates completed.")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    update_users() 