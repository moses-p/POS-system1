from app import app, db, User
from flask_mail import Message
import sys

def check_db():
    try:
        with app.app_context():
            db.session.execute('SELECT 1')
            print("Database connection: OK")
            # Check tables
            tables = db.engine.table_names() if hasattr(db.engine, 'table_names') else db.inspect(db.engine).get_table_names()
            for t in ['user', 'product', 'order', 'order_item']:
                if t not in tables:
                    print(f"Table missing: {t}")
                    return False
            print("All required tables exist.")
            return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

def check_admin():
    try:
        with app.app_context():
            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                print(f"Admin user exists: {admin.username}")
                return True
            else:
                print("No admin user found!")
                return False
    except Exception as e:
        print(f"Admin check failed: {e}")
        return False

def check_email():
    try:
        with app.app_context():
            from flask_mail import Mail
            mail = Mail(app)
            msg = Message("Health Check", recipients=[app.config['MAIL_DEFAULT_SENDER']], body="Health check email.")
            mail.send(msg)
            print("Email sending: OK")
            return True
    except Exception as e:
        print(f"Email check failed: {e}")
        return False

if __name__ == '__main__':
    all_ok = check_db() and check_admin() and check_email()
    sys.exit(0 if all_ok else 1) 