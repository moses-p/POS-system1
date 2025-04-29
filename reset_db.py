from app import app, db, User, Order
import os

def reset_database():
    print("Resetting database...")
    
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        
        # Create all tables with the updated schema
        db.create_all()
        
        # Recreate the admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        
        # Recreate the staff user
        staff = User(
            username='staff',
            email='staff@example.com',
            is_staff=True
        )
        staff.set_password('staff123')
        
        # Add users to database
        db.session.add(admin)
        db.session.add(staff)
        
        # Commit changes
        db.session.commit()
        
        print("Database reset complete. Default users created:")
        print("- Admin: username=admin, password=admin123")
        print("- Staff: username=staff, password=staff123")

if __name__ == "__main__":
    # Check if the user really wants to reset the database
    confirm = input("This will delete ALL data in the database. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Database reset cancelled.") 