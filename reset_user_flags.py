from app import db, User, app

def get_initials_from_username_or_email(user):
    # Use username if available, otherwise use email before @
    base = user.username or user.email.split("@")[0]
    # Split by non-alphabetic characters, take first letters, uppercase
    parts = [p for p in base.replace('.', ' ').replace('_', ' ').split() if p]
    if len(parts) == 1:
        return parts[0][0].upper()
    elif len(parts) > 1:
        return ''.join([p[0].upper() for p in parts[:2]])
    else:
        return base[0].upper()

with app.app_context():
    users = User.query.all()
    # Special case for Fiona
    fiona = User.query.filter_by(username='Fiona').first()
    if fiona:
        fiona.full_name = 'Fiona'
        fiona.update_initials()
        print(f"Fiona updated: full_name={fiona.full_name}, initials={fiona.initials}")
    for u in users:
        # Always set initials from username or email
        u.initials = get_initials_from_username_or_email(u)
        # Clear full_name
        u.full_name = ""
        u.welcome_email_sent = False
        print(f"Updated: {u.username} | initials={u.initials} | welcome_email_sent={u.welcome_email_sent}")
    db.session.commit()
    print("\nAll users have initials set from username/email, full_name cleared, and welcome_email_sent reset.")

    # Print all users for verification
    print("\n--- User List ---")
    for u in users:
        print(f"Username: {u.username} | Initials: {u.initials}") 