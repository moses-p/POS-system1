from app import app, db, User

def make_admin(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"Successfully made {username} an admin!")
        else:
            print(f"User {username} not found!")

if __name__ == "__main__":
    username = input("Enter the username to make admin: ")
    make_admin(username) 