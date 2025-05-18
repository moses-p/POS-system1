from app import app, db, User
import sys

def create_initial_admin():
    """Create initial admin user if none exists"""
    try:
        with app.app_context():
            # Check if any admin exists
            admin_exists = User.query.filter_by(is_admin=True).first()
            
            if admin_exists:
                print("An admin user already exists. Skipping admin creation.")
                return False
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True,
                is_staff=True,
                full_name='System Administrator'
            )
            admin.set_password('admin123')
            
            # Add to database
            db.session.add(admin)
            db.session.commit()
            
            print("Initial admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("\nIMPORTANT: Please change the admin password after first login!")
            return True
            
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_initial_admin()
    sys.exit(0 if success else 1) 