from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from datetime import datetime

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Order model to match what's in app.py
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    
    # Customer contact information for guest checkouts or in-store sales
    customer_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    customer_email = db.Column(db.String(100), nullable=True)
    customer_address = db.Column(db.Text, nullable=True)
    
    # Order type
    order_type = db.Column(db.String(20), default='online')  # 'online', 'in-store'
    # Who created the order (staff member or system for online orders)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Status change timestamps
    updated_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Order notification status
    viewed = db.Column(db.Boolean, default=False)
    viewed_at = db.Column(db.DateTime, nullable=True)

# Verify the model
with app.app_context():
    # Get table inspector
    inspector = inspect(db.engine)
    
    # Get table columns
    columns = inspector.get_columns('order')
    
    print("SQLAlchemy Model - Order Table Columns:")
    print("=======================================")
    for column in columns:
        print(f"{column['name']}: {column['type']} (nullable: {column['nullable']})")
    
    # Check for viewed column
    if any(col['name'] == 'viewed' for col in columns):
        print("\n✓ 'viewed' column exists in database schema")
    else:
        print("\n✗ 'viewed' column MISSING from database schema")
    
    # Check for viewed_at column
    if any(col['name'] == 'viewed_at' for col in columns):
        print("✓ 'viewed_at' column exists in database schema")
    else:
        print("✗ 'viewed_at' column MISSING from database schema")
    
    # Look at existing data
    print("\nChecking existing orders:")
    orders = db.session.query(Order).order_by(Order.id.desc()).limit(3).all()
    for order in orders:
        print(f"Order #{order.id}: Status={order.status}, Viewed={order.viewed}, Viewed_at={order.viewed_at}") 