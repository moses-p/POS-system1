from app import app, db, User

# Function to create admin and staff users
def create_users():
    with app.app_context():
        # Reset admin user if it exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.set_password('admin123')
            print(f"Reset password for existing admin user: {admin.username}")
        else:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("Created new admin user")
        
        # Create staff user if it doesn't exist or update existing one
        staff = User.query.filter_by(username='staff').first()
        if not staff:
            staff = User(
                username='staff',
                email='staff@example.com',
                is_staff=True,
                is_admin=True  # Give staff user admin privileges
            )
            staff.set_password('staff123')
            db.session.add(staff)
            print("Created new staff user with admin privileges")
        else:
            staff.is_staff = True
            staff.is_admin = True  # Update existing staff user to have admin privileges
            staff.set_password('staff123')
            print(f"Reset password for existing staff user and granted admin privileges: {staff.username}")
        
        # Commit all changes
        db.session.commit()
        print("All user changes committed to database")

if __name__ == '__main__':
    create_users() 