
# Update the Order model in app.py

class Order(db.Model):
    # Note: SQLAlchemy will use the __tablename__ value as the table name
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    items = db.relationship('OrderItem', backref='order', lazy=True)
    
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
    
    # Order notification status - explicitly define these columns
    viewed = db.Column(db.Boolean, default=False)
    viewed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships with clear names
    customer = db.relationship('User', foreign_keys=[customer_id], backref='orders')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_orders')
