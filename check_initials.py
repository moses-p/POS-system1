from app import db, User
user = User.query.filter_by(username='Eddy Mutwe').first()
print('Initials:', user.initials if user else 'User not found') 