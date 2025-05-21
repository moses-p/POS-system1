import os
import sys
from app import app, db, User

def remove_user_by_email(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            print(f"User with email '{email}' removed.")
        else:
            print(f"No user found with email '{email}'.")

def create_admin(username, email, password):
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return
        admin = User(username=username, email=email, is_admin=True, is_staff=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)
    username, email, password = sys.argv[1:4]
    remove_user_by_email(email)
    create_admin(username, email, password)

with app.app_context():
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully!')
    else:
        print('Admin user already exists.')
        
    # Also create a staff user
    staff = User.query.filter_by(username='staff').first()
    if not staff:
        staff = User(
            username='staff',
            email='staff@example.com',
            is_admin=False
        )
        staff.set_password('staff123')
        db.session.add(staff)
        db.session.commit()
        print('Staff user created successfully!')
    else:
        print('Staff user already exists.') 