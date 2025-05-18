from app import app, db, User
import re

def generate_initials(full_name):
    """Generate initials from full name."""
    if not full_name:
        return ''
    
    # Split name into words and get first letter of each
    words = full_name.split()
    if not words:
        return ''
    
    # Get first letter of each word, up to 4 letters
    initials = ''.join(word[0].upper() for word in words[:4])
    return initials

def backfill_initials():
    """Backfill initials for all users."""
    with app.app_context():
        users = User.query.all()
        updated = 0
        
        for user in users:
            if not user.initials:
                # If no full_name, use username as fallback
                if not user.full_name:
                    user.full_name = user.username
                
                user.initials = generate_initials(user.full_name)
                updated += 1
                print(f"Updated user {user.username}: {user.initials}")
        
        if updated > 0:
            db.session.commit()
            print(f"\nSuccessfully updated {updated} users.")
        else:
            print("\nNo users needed updating.")

if __name__ == '__main__':
    backfill_initials() 