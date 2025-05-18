import os
import shutil
from datetime import datetime

def ensure_backup_dir():
    if not os.path.exists('backups'):
        os.makedirs('backups')
        print("Created backups/ directory.")

def backup_database():
    db_path = os.path.join('instance', 'pos.db')
    if not os.path.exists(db_path):
        print("Database file not found!")
        return False
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join('backups', f'pos_{timestamp}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to {backup_path}")
    return True

def backup_uploads():
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        print("No uploads/ directory to back up.")
        return True
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join('backups', f'uploads_{timestamp}')
    shutil.copytree(uploads_dir, backup_dir)
    print(f"Uploads backed up to {backup_dir}")
    return True

def main():
    ensure_backup_dir()
    db_ok = backup_database()
    uploads_ok = backup_uploads()
    if db_ok and uploads_ok:
        print("Backup completed successfully.")
    else:
        print("Backup completed with some issues.")

if __name__ == '__main__':
    main() 