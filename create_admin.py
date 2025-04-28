from app import app, db, User

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