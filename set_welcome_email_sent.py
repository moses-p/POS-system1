from app import app, db, User
import sys

def reset_welcome_email(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.welcome_email_sent = False
            db.session.commit()
            print(f"welcome_email_sent reset to 0 for user: {email}")
        else:
            print(f"No user found with email: {email}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python set_welcome_email_sent.py <email>")
        sys.exit(1)
    reset_welcome_email(sys.argv[1]) 