from app import app, db, User

with app.app_context():
    # Drop all existing tables
    db.drop_all()
    
    # Create all tables with the new schema
    db.create_all()
    
    # Create admin user
    admin = User(username='admin', email='admin@example.com', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create staff user
    staff = User(username='staff', email='staff@example.com', is_admin=False)
    staff.set_password('staff123')
    db.session.add(staff)
    
    db.session.commit()
    
    print("Database initialized successfully!") 