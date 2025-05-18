from app import db, User, app

with app.app_context():
    print('--- All Users ---')
    for u in User.query.all():
        print(f"Username: {u.username}, Email: {u.email}, Admin: {u.is_admin}, Staff: {u.is_staff}, Password Hash: {u.password_hash}")

    user = User.query.filter_by(username='given').first()
    if user:
        user.set_password('given123')
        db.session.commit()
        print("\nPassword for 'given' has been reset to 'given123'.")
    else:
        user = User(username='given', email='given@example.com', is_admin=True, is_staff=True, full_name='Given Admin', initials='GA')
        user.set_password('given123')
        db.session.add(user)
        db.session.commit()
        print("\nUser 'given' created as admin with password 'given123'.") 