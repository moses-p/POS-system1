print('HELLO FROM FLASK')
import os
import uuid
import json
import time
import base64
import logging
import requests
import hashlib
import mimetypes
import sqlite3
import tempfile
import sys
from datetime import datetime, timedelta, date, timezone, UTC
from types import SimpleNamespace
from flask import Flask, render_template, redirect, request, url_for, flash, jsonify, session, abort, send_file, make_response, g, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from sqlalchemy import text, func
from werkzeug.utils import secure_filename
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature
from PIL import Image, ImageOps
import qrcode
from io import BytesIO
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from sql_operations import direct_get_order, direct_cart_operations, direct_get_products, direct_create_user, direct_get_user, direct_create_product, get_db_connection
from direct_create_order import direct_create_order
import pytz
from sqlalchemy import event
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit

# Define what's available for import
__all__ = ['app', 'init_db', 'db']

# Generate a version ID for this app instance - changes on server restart
APP_VERSION = str(uuid.uuid4())[:8]
# Use a stable timestamp that only changes when the server restarts
APP_TIMESTAMP = str(int(datetime.now().timestamp()))

# Simple relativedelta alternative to add months
def add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return dt.replace(year=year, month=month, day=day)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_staff and not current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath('instance/pos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in files
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)  # Session expiration time

# Ensure static files are found correctly
app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.static_url_path = '/static'

# Enable CORS for all routes
CORS(app)

# Enable debug mode
app.debug = True

# Custom render_template that adds version parameter
def versioned_render_template(*args, **kwargs):
    """Add version to all templates for cache busting"""
    try:
        # Debug print to help locate the active template
        print(f"[DEBUG] Rendering template: {args[0] if args else 'UNKNOWN'} | CWD: {os.getcwd()}")
        # Ensure we have a valid template and then add version
        kwargs['version'] = APP_VERSION
        kwargs['timestamp'] = APP_TIMESTAMP
        
        # Add common template variables
        kwargs.setdefault('is_mobile', is_mobile() if 'is_mobile' in globals() else False)
        
        # Ensure the first argument is a valid template
        if not args or not isinstance(args[0], str):
            logger.error(f"Invalid template name: {args}")
            return render_template('error.html', error="Template rendering error"), 500
            
        return render_template(*args, **kwargs)
    except Exception as e:
        logger.error(f"Template rendering error: {str(e)}")
        # Fallback to basic rendering of error template
        try:
            return render_template('error.html', error=str(e)), 500
        except:
            # Ultimate fallback - plain text response
            return f"Error: {str(e)}", 500

# Add error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Server Error: {error}')
    db.session.rollback()
    return versioned_render_template('error.html', error=error), 500

@app.errorhandler(403)
def forbidden_error(error):
    logger.error(f"403 error: {error}")
    try:
        return versioned_render_template('error.html', error=error), 403
    except Exception as e:
        logger.error(f"Error rendering 403 template: {e}")
        # Fallback to static error page
        return send_file('templates/error_fallback.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    """Custom handler for 404 errors to prevent them from turning into 403 errors"""
    logger.warning(f"404 error: {error} - Path: {request.path}")
    
    # For API requests return JSON
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found", "path": request.path}), 404
        
    # For static files, serve a default version if possible
    if request.path.startswith('/static/'):
        file_type = request.path.split('.')[-1] if '.' in request.path else ''
        if file_type == 'js':
            return "console.log('File not found');", 200, {'Content-Type': 'application/javascript'}
        elif file_type == 'css':
            return "/* File not found */", 200, {'Content-Type': 'text/css'}
        elif file_type in ['png', 'jpg', 'jpeg', 'gif']:
            # Could serve a default image here if needed
            pass
    
    try:
        return versioned_render_template('error.html', error=error), 404
    except Exception as e:
        logger.error(f"Error rendering 404 template: {e}")
        # Fallback to static error page
        return send_file('templates/error_fallback.html'), 404

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f'Unhandled Exception: {str(e)}')
    try:
        return versioned_render_template('error.html', error=str(e)), 500
    except Exception as err:
        logger.error(f"Error rendering exception template: {err}")
        # Fallback to static error page
        return send_file('templates/error_fallback.html'), 500

# Add security headers and disable caching
@app.after_request
def add_headers(response):
    """Add security and cache control headers to responses"""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Set Cache-Control header for static assets
    if '/static/' in request.path:
        # Cache static files for longer with a version parameter for cache busting
        max_age = 60 * 60 * 24 * 30  # 30 days
        response.headers['Cache-Control'] = f'public, max-age={max_age}'
    else:
        # For dynamic routes, avoid caching sensitive content
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    
    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    # Add Content-Security-Policy to prevent mixed content issues
    response.headers['Content-Security-Policy'] = "default-src 'self' http: https: data: blob: 'unsafe-inline' 'unsafe-eval'"
    
    return response

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(120), nullable=False, default='')
    initials = db.Column(db.String(4), nullable=False, default='')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    # Add location fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(200), nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    welcome_email_sent = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_initials(self):
        """Update initials based on full_name."""
        self.initials = generate_initials(self.full_name)

@event.listens_for(User, 'before_insert')
def receive_before_insert(mapper, connection, target):
    """Generate initials before inserting a new user."""
    if not target.initials:
        target.update_initials()

@event.listens_for(User, 'before_update')
def receive_before_update(mapper, connection, target):
    """Update initials when full_name changes."""
    if target.full_name and not target.initials:
        target.update_initials()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)  # Selling price
    buying_price = db.Column(db.Float, nullable=False)  # Cost price
    currency = db.Column(db.String(3), nullable=False, default='UGX')
    stock = db.Column(db.Float, nullable=False, default=0)
    max_stock = db.Column(db.Float, nullable=False, default=0)
    reorder_point = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(10), nullable=False, default='pcs')
    category = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    barcode = db.Column(db.String(50), unique=True, nullable=True, default=None)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    stock_movements = db.relationship('StockMovement', backref='product', lazy=True)
    low_stock_threshold = db.Column(db.Float, nullable=False, default=5.0)

    @property
    def profit_margin(self):
        """Calculate profit margin as a percentage"""
        if self.buying_price == 0:
            return 0
        return ((self.price - self.buying_price) / self.buying_price) * 100

    @property
    def stock_status(self):
        if self.stock <= self.reorder_point:
            return 'low'
        elif self.stock >= self.max_stock * 0.9:
            return 'high'
        return 'normal'

    @property
    def stock_percentage(self):
        return (self.stock / self.max_stock) * 100 if self.max_stock > 0 else 0

    def update_stock(self, quantity, movement_type, notes=None):
        """
        Update product stock and create a stock movement record
        Args:
            quantity: The quantity to add/remove
            movement_type: 'sale' or 'restock'
            notes: Optional notes for the stock movement record
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate inputs
            if quantity <= 0:
                logger.warning(f"Invalid quantity {quantity} for stock update of product {self.id}")
                return False
            quantity = float(quantity)
            old_stock = float(self.stock)
            if movement_type == 'sale':
                if old_stock < quantity:
                    logger.warning(f"Attempted to sell {quantity} of product {self.id} but only {old_stock} available")
                    return False
                actual_quantity = quantity
                self.stock = max(0.0, old_stock - quantity)
            elif movement_type == 'restock':
                actual_quantity = quantity
                self.stock = old_stock + quantity
            else:
                logger.warning(f"Invalid movement type {movement_type} for product {self.id}")
                return False
            self.stock = max(0.0, float(self.stock))
            logger.info(f"Stock update for product {self.id}: {movement_type} of {actual_quantity}, old_stock={old_stock}, new_stock={self.stock}")
            self.updated_at = datetime.now(UTC)
            movement = StockMovement(
                product_id=self.id,
                quantity=actual_quantity,
                movement_type=movement_type,
                remaining_stock=self.stock,
                timestamp=datetime.now(UTC),
                notes=notes
            )
            db.session.add(movement)
            db.session.add(self)
            return True
        except Exception as e:
            logger.error(f"Error updating stock for product {self.id}: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False

    def __repr__(self):
        return f'<Product {self.name}>'

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Quantity in kgs/ltrs
    movement_type = db.Column(db.String(20), nullable=False)  # 'sale' or 'restock'
    remaining_stock = db.Column(db.Float, nullable=False)  # Stock level after movement
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    notes = db.Column(db.Text)

class PriceChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    
    # Relationships
    product = db.relationship('Product', backref='price_history')
    changed_by = db.relationship('User', backref=db.backref('price_changes', passive_deletes=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    order_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='pending')
    customer_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    customer_email = db.Column(db.String(100), nullable=True)
    customer_address = db.Column(db.Text, nullable=True)
    order_type = db.Column(db.String(20), default='online')  # 'online', 'in-store'
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    viewed = db.Column(db.Boolean, default=False)
    viewed_at = db.Column(db.DateTime, nullable=True)
    payment_status = db.Column(db.String(20), nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    
    # Relationships with clear names
    customer = db.relationship('User', foreign_keys=[customer_id], backref=db.backref('orders', passive_deletes=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref=db.backref('created_orders', passive_deletes=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product', backref='order_items')
    
    # Added to calculate subtotal
    @property
    def subtotal(self):
        return self.quantity * self.price

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)  # Make nullable for anonymous users
    status = db.Column(db.String(20), default='active')
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='cart_items')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/debug')
def debug_route():
    """Debug route to test basic access"""
    return jsonify({
        'status': 'success',
        'message': 'Debug route accessible',
        'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'route': request.path,
        'method': request.method,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/')
def index():
    # Improved version with product categories
    products = Product.query.order_by(Product.name).all()
    categories = get_grocery_categories()
    
    # Group products by category
    categorized_products = {}
    for product in products:
        if product.category not in categorized_products:
            categorized_products[product.category] = []
        categorized_products[product.category].append(product)
    
    # Create flat category list for dropdown
    flat_categories = []
    for category_group in categories:
        group_id, group_name, subcategories = category_group
        for subcat_id, subcat_name in subcategories:
            flat_categories.append((subcat_id, subcat_name, group_name))
    
    return versioned_render_template('index.html', 
                           products=products,
                           categorized_products=categorized_products,
                           categories=categories,
                           flat_categories=flat_categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print('--- LOGIN ROUTE HIT ---')
    if current_user.is_authenticated:
        print('Already authenticated:', current_user.username)
        if current_user.is_admin:
            print('Redirecting to admin')
            return redirect(url_for('admin'))
        elif current_user.is_staff:
            print('Redirecting to staff_orders')
            return redirect(url_for('staff_orders'))
        else:
            print('Redirecting to index')
            return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        print(f'POST login: username={username}, password={password}')
        user = User.query.filter_by(username=username).first()
        print('User found:', bool(user))
        if user:
            print('User is_admin:', user.is_admin)
            print('User is_staff:', user.is_staff)
            print('Checking password...')
            print('Password check:', user.check_password(password))
        if user and user.check_password(password):
            print('Password correct, logging in...')
            login_user(user, remember=remember)
            user.is_online = True  # Set online status
            db.session.commit()
            # --- EMAIL LOGIC START ---
            try:
                # Always notify admin on any login
                admin_user = User.query.filter_by(is_admin=True).first()
                if admin_user and admin_user.email and user.id != admin_user.id:
                    subject = f"User Login Notification: {user.username}"
                    body = f"User {user.full_name or user.username} (username: {user.username}, email: {user.email}) logged in at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    send_email(subject, [admin_user.email], body)
                # Send welcome/info email to regular users only once
                if not user.is_admin and not user.welcome_email_sent:
                    subject = "Welcome to Your POS System!"
                    body = f"Hello {user.full_name or user.username},\n\nThank you for logging in to the POS system. If you have any questions, reply to this email.\n\nBest regards,\nYour POS Team"
                    if send_email(subject, [user.email], body):
                        user.welcome_email_sent = True
                        db.session.commit()
            except Exception as e:
                app.logger.error(f"Failed to send login email: {e}")
            # --- EMAIL LOGIC END ---
            next_page = request.args.get('next')
            print('Next page:', next_page)
            if not next_page or url_parse(next_page).netloc != '':
                if user.is_admin:
                    next_page = url_for('admin')
                elif user.is_staff:
                    next_page = url_for('staff_orders')
                else:
                    next_page = url_for('index')
            print('Redirecting to:', next_page)
            return redirect(next_page)
        else:
            print('Invalid username or password')
            flash('Invalid username or password')
    return versioned_render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    from datetime import datetime, timedelta
    # Set last_seen to now and set is_online to False
    current_user.last_seen = datetime.utcnow()
    current_user.is_online = False
    db.session.commit()
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    if request.method == 'POST':
        try:
            # Get form data
            email = request.form.get('email')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate email
            if email != current_user.email:
                # Check if the email is already in use by another user
                existing_user = User.query.filter(User.email == email, User.id != safe_user_id()).first()
                if existing_user:
                    flash('Email is already in use by another account', 'danger')
                    return redirect(url_for('profile'))
                    
                # Update email
                current_user.email = email
                flash('Email updated successfully', 'success')
            
            # Check if password change was requested
            if current_password and new_password:
                # Verify current password
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect', 'danger')
                    return redirect(url_for('profile'))
                
                # Confirm new password match
                if new_password != confirm_password:
                    flash('New passwords do not match', 'danger')
                    return redirect(url_for('profile'))
                
                # Update password
                current_user.set_password(new_password)
                flash('Password updated successfully', 'success')
            
            # Save changes
            db.session.commit()
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating profile: {str(e)}')
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('profile'))
    
    # GET request - show the form
    return render_template('profile.html')

@app.route('/admin')
@login_required
@admin_required
def admin():
    # Get all products
    products = Product.query.all()
    
    # Get admin users
    admin_users = User.query.filter_by(is_admin=True).all()
    
    # Get staff locations
    staff_locations = User.query.filter_by(is_staff=True).all()
    
    # Get recent stock movements
    recent_movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(10).all()
    
    # Get sales data for the chart
    dates = []
    sales_data = []
    
    # Get sales for the last 7 days
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        daily_sales = Order.query.filter(
            func.date(Order.order_date) == date.date()
        ).with_entities(func.sum(Order.total_amount)).scalar() or 0
        
        dates.append(date.strftime('%Y-%m-%d'))
        sales_data.append(float(daily_sales))
    
    # Calculate today's sales
    today_sales = Order.query.filter(
        func.date(Order.order_date) == datetime.now().date()
    ).with_entities(func.sum(Order.total_amount)).scalar() or 0
    
    # Get product statistics
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock < Product.low_stock_threshold).count()
    out_of_stock_products = Product.query.filter(Product.stock <= 0).count()
    
    return render_template('admin.html',
                         products=products,
                         admin_users=admin_users,
                         staff_locations=staff_locations,
                         recent_movements=recent_movements,
                         dates=dates,
                         sales_data=sales_data,
                         today_sales=today_sales,
                         total_products=total_products,
                         low_stock_products=low_stock_products,
                         out_of_stock_products=out_of_stock_products)

@app.route('/inventory_management')
@login_required
@admin_required
def inventory_management():
    """Admin inventory management page"""
    try:
        # Get all products for inventory management
        products = Product.query.all()
        
        # Get recent stock movements
        recent_movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(20).all()
        
        # Get counts of product stock status
        low_stock_products = Product.query.filter(Product.stock <= Product.reorder_point).count()
        out_of_stock_products = Product.query.filter(Product.stock == 0).count()
        overstocked_products = Product.query.filter(Product.stock >= Product.max_stock).count()
        
        return render_template('inventory_management.html', 
                               products=products,
                               recent_movements=recent_movements,
                               low_stock_products=low_stock_products,
                               out_of_stock_products=out_of_stock_products,
                               overstocked_products=overstocked_products)
    except Exception as e:
        logger.error(f'Error in inventory management route: {str(e)}')
        flash('An error occurred while loading the inventory management page', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/create_admin', methods=['GET', 'POST'])
@login_required
@admin_required
def create_admin():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not all([username, email, password]):
                flash('Please fill in all fields', 'error')
                return redirect(url_for('create_admin'))
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('create_admin'))
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return redirect(url_for('create_admin'))
            
            admin = User(username=username, email=email, is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            
            flash('Admin user created successfully', 'success')
            return redirect(url_for('admin'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating admin user: {str(e)}')
            flash('An error occurred while creating the admin user', 'error')
            return redirect(url_for('create_admin'))
    
    return render_template('create_admin.html')

@app.route('/admin/manage_staff', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_staff():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('manage_staff'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('manage_staff'))
        
        user = User(username=username, email=email, is_staff=True, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Staff user created successfully', 'success')
        return redirect(url_for('manage_staff'))
    
    staff_users = User.query.filter_by(is_staff=True).all()
    return render_template('manage_staff.html', staff_users=staff_users)

@app.route('/admin/delete_staff/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_staff(user_id):
    user = User.query.get_or_404(user_id)
    
    # Don't allow deleting your own account
    if user.id == safe_user_id():
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('manage_staff'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Staff user "{username}" has been deleted', 'success')
        return redirect(url_for('manage_staff'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting staff user: {str(e)}")
        flash(f'An error occurred while deleting the staff user: {str(e)}', 'danger')
        return redirect(url_for('manage_staff'))

@app.route('/admin/edit_staff/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_staff(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        is_admin = 'is_admin' in request.form
        
        # Check if email is already in use by another user
        if email != user.email:
            existing_user = User.query.filter(User.email == email, User.id != safe_user_id()).first()
            if existing_user:
                flash('Email is already in use by another user', 'danger')
                return redirect(url_for('edit_staff', user_id=user.id))
            
            user.email = email
        
        # Update password if provided
        if new_password:
            user.set_password(new_password)
        
        # Update admin status
        user.is_admin = is_admin
        
        db.session.commit()
        flash('Staff user updated successfully', 'success')
        return redirect(url_for('manage_staff'))
    
    return render_template('edit_staff.html', user=user)

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Don't allow removing admin from your own account
    if user.id == safe_user_id():
        flash('You cannot remove admin privileges from your own account', 'danger')
        return redirect(url_for('manage_staff'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'granted' if user.is_admin else 'removed'
    flash(f'Admin privileges {status} for {user.username}', 'success')
    return redirect(url_for('manage_staff'))

@app.route('/cart')
def view_cart():
    try:
        # Get or create active cart
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=safe_user_id(), status='active').first()
        else:
            # For anonymous users, use session to track cart
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = safe_user_id()
            db.session.add(cart)
            db.session.commit()
            if not current_user.is_authenticated:
                session['cart_id'] = cart.id
        
        # Validate cart items and remove any invalid ones (always fetch latest product info)
        invalid_items = []
        for item in cart.items:
            # Always fetch the latest product info from the database
            product = Product.query.get(item.product_id)
            if not product or product.stock <= 0 or item.quantity <= 0:
                invalid_items.append(item)
            else:
                # Update the item.product reference to the latest product
                item.product = product
        
        if invalid_items:
            for item in invalid_items:
                db.session.delete(item)
            db.session.commit()
            flash('Some items were removed from your cart because they are no longer available', 'warning')
        
        # Get cart items and calculate total
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        total_amount = sum(item.quantity * Product.query.get(item.product_id).price for item in cart_items)
        
        return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)
    except Exception as e:
        logger.error(f'Error viewing cart: {str(e)}')
        flash('An error occurred while loading your cart', 'error')
        return redirect(url_for('index'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    try:
        # Lock to prevent race conditions by getting the latest product data
        product = Product.query.get_or_404(product_id)
        
        if product.stock <= 0:
            return jsonify({'success': False, 'error': 'Product out of stock'}), 400

        # Get customer information from request
        data = request.get_json() or {}
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        customer_email = data.get('customer_email', '')
        customer_address = data.get('customer_address', '')
        
        # Get or create active cart
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=safe_user_id(), status='active').first()
        else:
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = safe_user_id()
            
            # Store customer info in the session
            session['customer_name'] = customer_name
            session['customer_phone'] = customer_phone
            session['customer_email'] = customer_email
            session['customer_address'] = customer_address
            
            db.session.add(cart)
            db.session.commit()
            if not current_user.is_authenticated:
                session['cart_id'] = cart.id
        else:
            # Update customer info in the session if provided
            if customer_name:
                session['customer_name'] = customer_name
            if customer_phone:
                session['customer_phone'] = customer_phone
            if customer_email:
                session['customer_email'] = customer_email
            if customer_address:
                session['customer_address'] = customer_address
        
        # Add or update cart item with fresh stock check
        product = Product.query.get_or_404(product_id)  # Re-query to get most up-to-date stock
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        
        if cart_item:
            if cart_item.quantity + 1 > product.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item.quantity += 1
        else:
            if product.stock < 1:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            db.session.add(cart_item)
        
        db.session.commit()
        
        # Return cart count and total in the response for UI update
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        cart_count = sum(item.quantity for item in cart_items)
        cart_total = sum(item.quantity * item.product.price for item in cart_items)
        
        return jsonify({
            'success': True, 
            'message': 'Product added to cart',
            'cart_count': cart_count,
            'cart_total': cart_total,
            'product_name': product.name
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding to cart: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

def get_cart():
    """
    Helper function to get or create active cart for current user or session
    Returns the cart object or None if there's an error
    """
    try:
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=safe_user_id(), status='active').first()
        else:
            # For anonymous users, use session to track cart
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = safe_user_id()
            db.session.add(cart)
            db.session.commit()
            if not current_user.is_authenticated:
                session['cart_id'] = cart.id
        
        return cart
    except Exception as e:
        logger.error(f'Error getting cart: {str(e)}')
        return None

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Get cart items
    cart = get_cart()
    if not cart or not cart.items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    # Convert cart items to list
    cart_items = []
    insufficient_stock = []
    
    for item in cart.items:
        # Check stock levels before checkout
        product = Product.query.get(item.product_id)
        if product and product.stock < item.quantity:
            insufficient_stock.append({
                'product': product.name,
                'requested': item.quantity,
                'available': product.stock
            })
        
        cart_items.append({
            'product_id': item.product_id,
            'quantity': item.quantity,
            'price': item.product.price,
            'product_name': item.product.name
        })
    
    # Alert user if any products have insufficient stock
    if insufficient_stock:
        for item in insufficient_stock:
            flash(f"Insufficient stock for {item['product']}: requested {item['requested']}, only {item['available']} available", 'danger')
        return redirect(url_for('view_cart'))
    
    try:
        # Get the correct cart - same logic as in view_cart
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=safe_user_id(), status='active').first()
        else:
            # For anonymous users, use session to track cart
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart or not cart.items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('view_cart'))

        # Validate cart items and remove any invalid ones
        invalid_items = []
        for item in cart.items:
            if not item.product or item.product.stock <= 0 or item.quantity <= 0:
                invalid_items.append(item)
        
        if invalid_items:
            for item in invalid_items:
                db.session.delete(item)
            db.session.commit()
            flash('Some items were removed from your cart because they are no longer available', 'warning')
            if not cart.items:
                flash('Your cart is now empty', 'error')
                return redirect(url_for('view_cart'))

        if request.method == 'GET':
            # Calculate total for display
            try:
                # Ensure we calculate with the most up-to-date product prices
                total_amount = sum(item.quantity * item.product.price for item in cart.items)
            except Exception as calc_err:
                logger.error(f"Error calculating cart total: {str(calc_err)}")
                total_amount = 0
                for item in cart.items:
                    try:
                        item_total = item.quantity * item.product.price
                        total_amount += item_total
                    except:
                        # Skip items that can't be calculated
                        pass
            
            # Pass stored customer info to the template
            customer_info = {
                'name': session.get('customer_name', ''),
                'phone': session.get('customer_phone', ''),
                'email': session.get('customer_email', ''),
                'address': session.get('customer_address', '')
            }
            
            return render_template('checkout.html', cart=cart, total_amount=total_amount, customer_info=customer_info)

        # POST method - process the checkout
        try:
            # Get customer information
            customer_data = {
                'customer_name': request.form.get('customer_name', session.get('customer_name', '')),
                'customer_email': request.form.get('customer_email', session.get('customer_email', '')),
                'customer_phone': request.form.get('customer_phone', session.get('customer_phone', '')),
                'customer_address': request.form.get('customer_address', session.get('customer_address', '')),
                'created_by_id': safe_user_id() if current_user.is_authenticated else None
            }
            
            # Prepare items data from cart
            items_data = []
            for item in cart.items:
                if not item.product:
                    continue
                    
                # Fetch the latest product data to ensure stock accuracy
                product = Product.query.get(item.product_id)
                if not product:
                    continue
                    
                # Verify stock availability
                if item.quantity > product.stock:
                    flash(f'Not enough stock for {product.name}. Only {product.stock} available.', 'error')
                    return redirect(url_for('view_cart'))
                    
                # Add item to the list
                items_data.append({
                    'product_id': product.id,
                    'quantity': item.quantity,
                    'price': product.price,
                    'name': product.name
                })
            
            # Use the centralized function to create the order
            order, error = create_order(customer_data, items_data, 'online')
            logger.info(f'Order creation result: order={order}, error={error}')
            if order:
                logger.info(f'Created order ID: {getattr(order, "id", None)}')
            else:
                logger.warning('Order object is None after creation!')
            
            if error:
                # If it's a detected duplicate, we can still proceed to the receipt
                if "duplicate order" in error.lower() and hasattr(order, 'id') and order.id:
                    flash('It appears this order was already processed!', 'info')
                    # Mark cart as completed
                    cart.status = 'completed'
                    db.session.commit()
                    # Use get_order_by_id for more resilient order retrieval
                    order = get_order_by_id(order.id)
                    if order:
                        return redirect(url_for('print_receipt', order_id=order.id))
                    else:
                        flash('Order was created but could not be retrieved. Please check orders list.', 'warning')
                        return redirect(url_for('index'))
                elif "order created with id" in error.lower():
                    # This is not really an error - order was created but couldn't be retrieved as object
                    flash('Your order was successfully created!', 'success')
                    # Mark cart as completed
                    cart.status = 'completed'
                    db.session.commit()
                    # Extract order ID from the message
                    try:
                        import re
                        match = re.search(r'Order created with ID[:\s]*(\d+)', error)
                        if match:
                            order_id = int(match.group(1))
                            return redirect(url_for('print_receipt', order_id=order_id))
                    except Exception as e:
                        logger.error(f"Error extracting order ID from message: {error}, exception: {str(e)}")
                        
                    flash('Order was created but order ID could not be extracted. Please check your orders.', 'warning')
                    return redirect(url_for('index'))
                else:
                    # For other errors, show error and return to cart
                    flash(error, 'error')
                    return redirect(url_for('view_cart'))
            
            # Mark cart as completed
            cart.status = 'completed'
            db.session.commit()
            
            # Store the order ID in session to prevent duplicates
            session['last_order_id'] = order.id
            
            # Retrieve order using resilient method to avoid reference_number issues
            logger.info(f'Attempting to retrieve order with ID: {order.id}')
            order_obj = get_order_by_id(order.id)
            logger.info(f'get_order_by_id({order.id}) returned: {order_obj}')
            order = order_obj
            if not order:
                flash('Order was created but could not be retrieved. Please check your orders.', 'warning')
                return redirect(url_for('index'))
            
            # Redirect to receipt
            return redirect(url_for('print_receipt', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error during checkout: {str(e)}')
            flash(f'Error during checkout: {str(e)}', 'error')
            return redirect(url_for('view_cart'))
    except Exception as e:
        logger.error(f'Error accessing cart: {str(e)}')
        flash(f'Error processing your request: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/receipt/<int:order_id>')
def print_receipt(order_id):
    try:
        # Use our resilient get_order_by_id function
        order = get_order_by_id(order_id)
        if not order:
            # Try one more time with direct SQL as fallback
            try:
                conn = sqlite3.connect('instance/pos.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get basic order info
                cursor.execute("SELECT id, total_amount FROM 'order' WHERE id = ?", (order_id,))
                basic_order = cursor.fetchone()
                
                if basic_order:
                    # Get order items
                    cursor.execute("""
                        SELECT oi.product_id, oi.quantity, oi.price, p.name as product_name
                        FROM order_item oi
                        JOIN product p ON oi.product_id = p.id
                        WHERE oi.order_id = ?
                    """, (order_id,))
                    
                    items = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                    
                    # Create a minimal order object
                    from types import SimpleNamespace
                    
                    class MinimalOrderItem:
                        def __init__(self, data):
                            self.product_id = data['product_id']
                            self.quantity = data['quantity']
                            self.price = data['price']
                            self.product = SimpleNamespace(name=data['product_name'])
                            
                        @property
                        def subtotal(self):
                            return self.price * self.quantity
                    
                    order = SimpleNamespace(
                        id=basic_order['id'],
                        total_amount=basic_order['total_amount'],
                        reference_number=f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{order_id}",
                        order_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        status="completed",
                        items=[MinimalOrderItem(item) for item in items]
                    )
                    
                    flash('Limited order information available', 'warning')
            except Exception as direct_error:
                logger.error(f"Error in direct SQL fallback for receipt: {str(direct_error)}")
                flash('Order not found', 'error')
                return redirect(url_for('index'))
        
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Add tax rate for receipt calculations
        tax_rate = 0.18  # 18% VAT
        # Pass current_user to template even for anonymous users
        staff_initials = ""
        if hasattr(order, 'created_by_id') and order.created_by_id:
            staff_user = User.query.get(order.created_by_id)
            if staff_user:
                staff_initials = staff_user.initials
        return render_template('receipt.html', order=order, tax_rate=tax_rate, current_user=current_user, staff_initials=staff_initials)
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    try:
        # Use our resilient get_order_by_id function
        order = get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Check permission if it's a regular Order object
        if hasattr(order, 'customer_id') and order.customer_id != safe_user_id() and not (current_user.is_authenticated and current_user.is_admin):
            abort(403)
            
        return render_template('order_confirmation.html', order=order)
    except Exception as e:
        logger.error(f"Error loading order confirmation for order {order_id}: {str(e)}")
        flash(f"Error loading order details: {str(e)}", 'error')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error loading order confirmation for order {order_id}: {str(e)}")
        flash(f"Error loading order details: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/restock/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def restock_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            quantity = float(request.form.get('quantity', 0))
            if quantity <= 0:
                flash('Please enter a valid quantity', 'error')
            elif product.stock + quantity > product.max_stock:
                flash(f'Restocking this amount would exceed the maximum stock ({product.max_stock} {product.unit}).', 'error')
            else:
                product.update_stock(quantity, 'restock')
                db.session.commit()
                flash(f'Successfully restocked {quantity} {product.unit} of {product.name}', 'success')
                # Add refresh=true parameter to force a fresh reload
                return redirect(url_for('inventory_management', refresh=True, t=int(datetime.now().timestamp())))
        except ValueError:
            flash('Please enter a valid number', 'error')
    
    return render_template('restock.html', product=product)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    try:
        cart_item = CartItem.query.get_or_404(item_id)
        data = request.get_json()
        new_quantity = int(data.get('quantity', 1))
        
        if new_quantity <= 0:
            # Remove item if quantity is 0 or negative
            db.session.delete(cart_item)
        else:
            # Check if there's enough stock
            if new_quantity > cart_item.product.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item.quantity = new_quantity
        
        db.session.commit()
        
        # Calculate new cart total after update
        cart = Cart.query.get(cart_item.cart_id)
        cart_total = sum(item.quantity * item.product.price for item in cart.items)
        cart_count = sum(item.quantity for item in cart.items)
        
        return jsonify({
            'success': True, 
            'message': 'Cart updated successfully',
            'cart_total': cart_total,
            'cart_count': cart_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating cart: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = float(request.form.get('price', 0))
            buying_price = float(request.form.get('buying_price', 0))
            currency = request.form.get('currency', 'UGX')
            stock = float(request.form.get('stock', 0))
            max_stock = float(request.form.get('max_stock', 0))
            reorder_point = float(request.form.get('reorder_point', 0))
            unit = request.form.get('unit', 'pcs')
            category = request.form.get('category')
            barcode = request.form.get('barcode')
            
            if not name or price <= 0 or buying_price <= 0:
                flash('Please fill in all required fields with valid values', 'error')
                return redirect(url_for('add_product'))
            
            # Handle image upload
            image_url = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_url = filename
            
            product = Product(
                name=name,
                description=description,
                price=price,
                buying_price=buying_price,
                currency=currency,
                stock=stock,
                max_stock=max_stock,
                reorder_point=reorder_point,
                unit=unit,
                category=category,
                image_url=image_url,
                barcode=barcode
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product added successfully', 'success')
            return redirect(url_for('inventory_management'))
            
        except Exception as e:
            logger.error(f'Error adding product: {str(e)}')
            flash('Error adding product', 'error')
            return redirect(url_for('add_product'))
    
    return render_template(
        'add_product.html',
        currencies=get_currencies(),
        units=get_product_units(),
        categories=get_grocery_categories()
    )

@app.route('/scan_barcode', methods=['POST'])
@login_required
@staff_required
def scan_barcode():
    try:
        barcode = request.json.get('barcode')
        if not barcode:
            return jsonify({'success': False, 'error': 'No barcode provided'}), 400
        
        product = Product.query.filter_by(barcode=barcode).first()
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'stock': product.stock
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_to_cart_barcode', methods=['POST'])
def add_to_cart_barcode():
    try:
        barcode = request.json.get('barcode')
        if not barcode:
            return jsonify({'success': False, 'error': 'No barcode provided'}), 400
        
        product = Product.query.filter_by(barcode=barcode).first()
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        # Get or create active cart
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=safe_user_id(), status='active').first()
        else:
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = safe_user_id()
            db.session.add(cart)
            db.session.commit()
            if not current_user.is_authenticated:
                session['cart_id'] = cart.id
        
        # Add or update cart item
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
        if cart_item:
            if cart_item.quantity + 1 > product.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item.quantity += 1
        else:
            if product.stock < 1:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1)
            db.session.add(cart_item)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Product added to cart',
            'product': {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'quantity': cart_item.quantity
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding product to cart: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('reports.html')

@app.route('/api/sales/daily', methods=['GET'])
@login_required
@admin_required
def daily_sales():
    try:
        # Get number of days to show (default 30 days)
        try:
            days = int(request.args.get('days', 30))
            if days <= 0 or days > 365:
                return jsonify({'error': 'Days must be between 1 and 365'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid days parameter'}), 400
        
        # Calculate start and end dates
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Initialize data structures
        dates = []
        sales_data = []
        profit_data = []
        expenses_data = []
        net_profit_data = []
        
        # Generate list of dates
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        for date in dates:
            # Get total sales for the day
            daily_sales = db.session.query(db.func.sum(Order.total_amount)).filter(
                db.func.date(Order.order_date) == date
            ).scalar()
            
            daily_total = float(daily_sales) if daily_sales else 0.0
            sales_data.append(daily_total)
            
            # Calculate cost of goods sold
            daily_orders = Order.query.filter(db.func.date(Order.order_date) == date).all()
            cost_of_goods = 0.0
            
            for order in daily_orders:
                for item in order.items:
                    cost_of_goods += item.quantity * item.product.buying_price
            
            # Get daily expenses
            daily_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
                db.func.date(Expense.date) == date
            ).scalar()
            
            daily_expenses = float(daily_expenses) if daily_expenses else 0.0
            expenses_data.append(daily_expenses)
            
            # Calculate gross profit (sales - cost of goods)
            gross_profit = daily_total - cost_of_goods
            
            # Calculate net profit (gross profit - expenses)
            net_profit = gross_profit - daily_expenses
            
            profit_data.append(gross_profit)
            net_profit_data.append(net_profit)
        
        dates_str = [date.strftime('%Y-%m-%d') for date in dates]
        
        return jsonify({
            'dates': dates_str or [],
            'sales': sales_data or [],
            'profit': profit_data or [],  # for frontend compatibility
            'gross_profit': profit_data or [],
            'expenses': expenses_data or [],
            'net_profit': net_profit_data or []
        })
    
    except Exception as e:
        # Log detailed error information
        import traceback
        logger.error(f'Error in daily sales API: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sales/weekly', methods=['GET'])
@login_required
@admin_required
def weekly_sales():
    try:
        # Get number of weeks to show (default 12 weeks)
        try:
            weeks = int(request.args.get('weeks', 12))
            if weeks <= 0 or weeks > 52:
                return jsonify({'error': 'Weeks must be between 1 and 52'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid weeks parameter'}), 400
        
        # Calculate start and end dates
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks)
        
        # Initialize data structures
        weeks_data = []
        sales_data = []
        profit_data = []
        
        # Process each week
        current_date = start_date
        while current_date <= end_date:
            # Calculate week start and end
            week_start = current_date
            week_end = min(week_start + timedelta(days=6), end_date)
            
            # Get orders for the week using more efficient query
            weekly_total = db.session.query(db.func.sum(Order.total_amount)).filter(
                db.func.date(Order.order_date) >= week_start,
                db.func.date(Order.order_date) <= week_end
            ).scalar()
            
            # Add NULL check to avoid issues with NULL dates
            weekly_total = db.session.query(db.func.sum(Order.total_amount)).filter(
                db.func.date(Order.order_date) >= week_start,
                db.func.date(Order.order_date) <= week_end,
                Order.order_date.isnot(None)
            ).scalar()
            
            weekly_total = float(weekly_total) if weekly_total else 0.0
            sales_data.append(weekly_total)
            
            # Calculate profit (simplified as 20% of sales)
            weekly_profit = weekly_total * 0.2
            profit_data.append(weekly_profit)
            
            # Format week label
            week_label = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
            weeks_data.append(week_label)
            
            # Move to next week
            current_date += timedelta(days=7)
        
        return jsonify({
            'weeks': weeks_data,
            'sales': sales_data,
            'profit': profit_data
        })
    
    except Exception as e:
        # Log detailed error information
        import traceback
        logger.error(f'Error in weekly sales API: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sales/monthly', methods=['GET'])
@login_required
@admin_required
def monthly_sales():
    try:
        # Get number of months to show (default 12 months)
        try:
            months = int(request.args.get('months', 12))
            if months <= 0 or months > 36:
                return jsonify({'error': 'Months must be between 1 and 36'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid months parameter'}), 400
        
        # Calculate start and end dates
        end_date = datetime.now().date().replace(day=1)
        
        # Initialize data structures
        months_data = []
        sales_data = []
        profit_data = []
        expenses_data = []
        net_profit_data = []
        
        # Process each month
        for i in range(months-1, -1, -1):
            try:
                # Calculate month dates
                current_month = add_months(end_date, -i)
                next_month = add_months(current_month, 1)
                
                # Get orders for the month
                monthly_orders = Order.query.filter(
                    db.func.date(Order.order_date) >= current_month,
                    db.func.date(Order.order_date) < next_month
                ).all()
                
                # Calculate total sales
                monthly_total = sum(order.total_amount for order in monthly_orders)
                sales_data.append(monthly_total)
                
                # Calculate cost of goods sold
                cost_of_goods = 0.0
                for order in monthly_orders:
                    for item in order.items:
                        cost_of_goods += item.quantity * item.product.buying_price
                
                # Get monthly expenses
                monthly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
                    db.func.date(Expense.date) >= current_month,
                    db.func.date(Expense.date) < next_month
                ).scalar()
                
                monthly_expenses = float(monthly_expenses) if monthly_expenses else 0.0
                expenses_data.append(monthly_expenses)
                
                # Calculate gross profit (sales - cost of goods)
                gross_profit = monthly_total - cost_of_goods
                
                # Calculate net profit (gross profit - expenses)
                net_profit = gross_profit - monthly_expenses
                
                profit_data.append(gross_profit)
                net_profit_data.append(net_profit)
                
                # Format month label
                month_label = current_month.strftime('%B %Y')
                months_data.append(month_label)
            except Exception as month_err:
                logger.error(f'Error processing month {i}: {str(month_err)}')
                # Add zero values for months with errors to maintain data array length
                sales_data.append(0.0)
                profit_data.append(0.0)
                expenses_data.append(0.0)
                net_profit_data.append(0.0)
                months_data.append(f"Error: Month -{i}")
        
        return jsonify({
            'months': months_data,
            'sales': sales_data,
            'gross_profit': profit_data,
            'expenses': expenses_data,
            'net_profit': net_profit_data
        })
    
    except Exception as e:
        logger.error(f'Error in monthly sales API: {str(e)}')
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sales/yearly', methods=['GET'])
@login_required
@admin_required
def yearly_sales():
    try:
        # Get number of years to show (default 5 years)
        try:
            years_count = int(request.args.get('years', 5))
            if years_count <= 0 or years_count > 10:
                return jsonify({'error': 'Years must be between 1 and 10'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid years parameter'}), 400
        
        # Calculate start and end years
        current_year = datetime.now().year
        
        # Initialize data structures
        years_data = []
        sales_data = []
        profit_data = []
        expenses_data = []
        net_profit_data = []
        
        # Process each year
        for year in range(current_year - years_count + 1, current_year + 1):
            try:
                # Calculate year dates
                year_start = datetime(year, 1, 1).date()
                year_end = datetime(year, 12, 31).date()
                
                # Get orders for the year
                yearly_orders = Order.query.filter(
                    db.func.date(Order.order_date) >= year_start,
                    db.func.date(Order.order_date) <= year_end
                ).all()
                
                # Calculate total sales
                yearly_total = sum(order.total_amount for order in yearly_orders)
                sales_data.append(yearly_total)
                
                # Calculate cost of goods sold
                cost_of_goods = 0.0
                for order in yearly_orders:
                    for item in order.items:
                        cost_of_goods += item.quantity * item.product.buying_price
                
                # Get yearly expenses
                yearly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
                    db.func.date(Expense.date) >= year_start,
                    db.func.date(Expense.date) <= year_end
                ).scalar()
                
                yearly_expenses = float(yearly_expenses) if yearly_expenses else 0.0
                expenses_data.append(yearly_expenses)
                
                # Calculate gross profit (sales - cost of goods)
                gross_profit = yearly_total - cost_of_goods
                
                # Calculate net profit (gross profit - expenses)
                net_profit = gross_profit - yearly_expenses
                
                profit_data.append(gross_profit)
                net_profit_data.append(net_profit)
                
                # Add year label
                years_data.append(str(year))
            except Exception as year_err:
                logger.error(f'Error processing year {year}: {str(year_err)}')
                # Add zero values for years with errors to maintain data array length
                sales_data.append(0.0)
                profit_data.append(0.0)
                expenses_data.append(0.0)
                net_profit_data.append(0.0)
                years_data.append(str(year))
        
        return jsonify({
            'years': years_data,
            'sales': sales_data,
            'gross_profit': profit_data,
            'expenses': expenses_data,
            'net_profit': net_profit_data
        })
    
    except Exception as e:
        logger.error(f'Error in yearly sales API: {str(e)}')
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/quick_price_update/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def quick_price_update(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        new_price = float(request.form.get('price', 0))
        
        if new_price <= 0:
            flash('Please enter a valid price', 'error')
            return redirect(request.referrer or url_for('admin'))
            
        # Record old price for tracking
        old_price = product.price
        product.price = new_price
        
        # Add record to price history
        price_change = PriceChange(
            product_id=product.id,
            old_price=old_price,
            new_price=new_price,
            changed_by_id=safe_user_id() if current_user.is_authenticated else None
        )
        db.session.add(price_change)
        db.session.commit()
        
        flash(f'Price for {product.name} updated from {old_price:.2f} to {new_price:.2f}', 'success')
        return redirect(request.referrer or url_for('admin'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating price: {str(e)}')
        flash('Error updating price', 'error')
        return redirect(request.referrer or url_for('admin'))
        
@app.route('/price_history/<int:product_id>')
@login_required
@admin_required
def price_history(product_id):
    product = Product.query.get_or_404(product_id)
    price_changes = PriceChange.query.filter_by(product_id=product_id).order_by(PriceChange.timestamp.desc()).all()
    return render_template('price_history.html', product=product, price_changes=price_changes)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price', 0))
            product.buying_price = float(request.form.get('buying_price', 0))
            product.currency = request.form.get('currency', 'UGX')
            product.stock = float(request.form.get('stock', 0))
            product.max_stock = float(request.form.get('max_stock', 0))
            product.reorder_point = float(request.form.get('reorder_point', 0))
            product.unit = request.form.get('unit', 'pcs')
            product.category = request.form.get('category')
            product.barcode = request.form.get('barcode')
            
            if not product.name or product.price <= 0 or product.buying_price <= 0:
                flash('Please fill in all required fields with valid values', 'error')
                return redirect(url_for('edit_product', product_id=product_id))
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    product.image_url = filename
            
            db.session.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('inventory_management'))
            
        except Exception as e:
            logger.error(f'Error updating product: {str(e)}')
            flash('Error updating product', 'error')
            return redirect(url_for('edit_product', product_id=product_id))
    
    return render_template(
        'edit_product.html',
        product=product,
        currencies=get_currencies(),
        units=get_product_units(),
        categories=get_grocery_categories()
    )

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        name = product.name
        
        # First delete related records
        StockMovement.query.filter_by(product_id=product_id).delete()
        PriceChange.query.filter_by(product_id=product_id).delete()
        OrderItem.query.filter_by(product_id=product_id).delete()
        CartItem.query.filter_by(product_id=product_id).delete()
        
        # Then delete the product itself
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Product "{name}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting product: {str(e)}')
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect(url_for('inventory_management'))

@app.route('/in_store_sale', methods=['GET', 'POST'])
@login_required
@staff_required
def in_store_sale():
    if request.method == 'GET':
        products = Product.query.all()
        # Check if there's an admin monitoring this session
        admin_monitoring = session.get('admin_monitoring_id')
        monitored_staff_id = session.get('monitored_staff_id')
        if admin_monitoring and monitored_staff_id:
            admin = User.query.get(admin_monitoring)
            monitored_staff = User.query.get(monitored_staff_id)
            if admin and admin.is_admin and monitored_staff:
                return render_template('in_store_sale.html', 
                                      products=products,
                                      admin_monitoring=admin,
                                      monitored_staff=monitored_staff)
        return render_template('in_store_sale.html', products=products)
    # Rest of the existing POST handling code...
    if not request.is_json:
        flash('Invalid request format', 'error')
        return redirect(url_for('in_store_sale'))
    try:
        data = request.get_json()
        # Always force created_by_id to current_user.id
        customer_data = {
            'customer_name': data.get('customer_name', ''),
            'customer_phone': data.get('customer_phone', ''),
            'customer_email': data.get('customer_email', ''),
            'customer_address': data.get('customer_address', ''),
            'created_by_id': safe_user_id() if current_user.is_authenticated else None
        }
        items_data = data.get('items', [])
        # Debug logging
        app.logger.info(f"[ORDER CREATE] User: {safe_user_id() or 'guest'} ({getattr(current_user, 'username', 'guest')}), customer_data: {customer_data}")
        # Verify stock levels before creating order
        stock_issues = []
        for item in items_data:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            
            product = Product.query.get(product_id)
            if not product:
                stock_issues.append(f"Product ID {product_id} not found")
                continue
                
            if product.stock < quantity:
                stock_issues.append(f"Insufficient stock for {product.name}: requested {quantity}, available {product.stock}")
        
        if stock_issues:
            return jsonify({
                'success': False,
                'error': "Stock verification failed",
                'issues': stock_issues
            }), 400
        
        # All stock checks passed, create the order
        order, error = create_order(customer_data, items_data, 'in-store')
        
        if order:
            # Create the reference number explicitly if it doesn't exist
            reference_number = None
            if hasattr(order, 'reference_number') and order.reference_number:
                reference_number = order.reference_number
            else:
                reference_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{order.id}"
            
            return jsonify({
                'success': True,
                'order_id': order.id,
                'reference': reference_number,
                'redirect_url': url_for('print_receipt', order_id=order.id)
            })
        else:
            # If the error message contains an order ID, try to use that
            order_id = None
            try:
                if error and "order created with id" in error.lower():
                    import re
                    match = re.search(r'Order created with ID[:\s]*(\d+)', error)
                    if match:
                        order_id = int(match.group(1))
            except Exception as e:
                logger.error(f"Error extracting order ID from message: {error}, exception: {str(e)}")
            
            if order_id:
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'reference': f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{order_id}",
                    'redirect_url': url_for('print_receipt', order_id=order_id)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': error or 'Unknown error creating order'
                }), 500
    except Exception as e:
        logger.error(f"Error processing in-store sale: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/pending_orders')
@login_required
def pending_orders_api():
    try:
        # Use direct SQL instead of ORM to avoid column issues
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Get online orders that are pending and haven't been processed
        cursor.execute("""
            SELECT id, customer_name, customer_phone, customer_email, customer_address, order_date, total_amount
            FROM 'order'
            WHERE order_type = 'online' AND status = 'pending'
            ORDER BY order_date DESC
            LIMIT 5
        """)
        
        pending_orders = cursor.fetchall()
        
        # Format the orders data for the response
        orders_data = []
        for order in pending_orders:
            # Get the order items count
            cursor.execute("SELECT COUNT(*) FROM order_item WHERE order_id = ?", (order[0],))
            items_count = cursor.fetchone()[0]
            
            # Format the order data
            orders_data.append({
                'id': order[0],
                'customer_name': order[1] or 'Online Customer',
                'order_date': order[5],
                'total_amount': float(order[6]),
                'items_count': items_count,
                'customer_phone': order[2] or '',
                'customer_email': order[3] or '',
                'customer_address': order[4] or ''
            })
        
        conn.close()
        
        return jsonify({
            'count': len(pending_orders),
            'orders': orders_data
        })
    except Exception as e:
        logger.error(f'Error fetching pending orders: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/mark_order_processed/<int:order_id>', methods=['POST'])
@login_required
def mark_order_processed(order_id):
    try:
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Update status to completed and set updated_at timestamp
        cursor.execute(
            "UPDATE 'order' SET status = 'completed', updated_at = ?, completed_at = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 
             order_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} marked as processed.'
        })
    except Exception as e:
        # Make sure to rollback on error
        try:
            conn.rollback()
            conn.close()
        except:
            pass
            
        logger.error(f'Error marking order as processed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def create_order(customer_data, items_data, order_type):
    """
    Centralized function to create orders from different contexts, with fallback to direct SQL
    """
    # Track which products have had stock reductions for rollback if needed
    stock_updates = []
    
    try:
        # First try using SQLAlchemy
        try:
            # Create a new order
            order = Order(
                customer_name=customer_data.get('customer_name', ''),
                customer_phone=customer_data.get('customer_phone', ''),
                customer_email=customer_data.get('customer_email', ''),
                customer_address=customer_data.get('customer_address', ''),
                total_amount=sum(item['price'] * item['quantity'] for item in items_data),
                order_type=order_type,
                customer_id=customer_data.get('customer_id'),
                created_by_id=customer_data.get('created_by_id')
            )
            
            # Add the order to the database
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Add order items
            for item_data in items_data:
                # Make sure the currency is UGX
                if 'currency' in item_data and item_data['currency'] != 'UGX':
                    logger.warning(f"Currency not UGX, overriding: {item_data['currency']} -> UGX")
                    item_data['currency'] = 'UGX'
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data['product_id'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                db.session.add(order_item)
                    
                # Update product stock
                product = Product.query.get(item_data['product_id'])
                if product:
                    # If currency default is not UGX, set it
                    if product.currency != 'UGX':
                        product.currency = 'UGX'
                        db.session.add(product)
                    
                    # Track stock update for possible rollback
                    stock_updates.append({
                        'product_id': product.id,
                        'quantity': item_data['quantity'],
                        'old_stock': product.stock
                    })
                    
                    # Update stock
                    success = product.update_stock(item_data['quantity'], 'sale')
                    if not success:
                        logger.error(f"Failed to update stock for product {product.id}")
                        raise Exception(f"Stock update failed for product {product.name}")
            
            # Generate reference number
            now = datetime.now(UTC)
            order.reference_number = f"ORD-{now.strftime('%Y%m%d')}-{order.id}"
            
            # Commit the transaction
            db.session.commit()
            
            # Return the created order
            return order, None
            
        except Exception as e:
            # If we get a SQLAlchemy error, try the direct SQL approach
            logger.warning(f"SQLAlchemy error when creating order, falling back to direct SQL: {str(e)}")
            db.session.rollback()
            
            # Restore stock levels
            if stock_updates:
                logger.info(f"Reverting {len(stock_updates)} stock updates before trying direct SQL")
                for update in stock_updates:
                    try:
                        product = Product.query.get(update['product_id'])
                        if product:
                            # Reset to original stock level
                            product.stock = update['old_stock']
                            db.session.add(product)
                    except Exception as revert_error:
                        logger.error(f"Error reverting stock for product {update['product_id']}: {str(revert_error)}")
                
                db.session.commit()
                stock_updates = []  # Clear the list for next attempt
            
            # Try direct SQL approach with current user ID if authenticated
            if current_user.is_authenticated:
                customer_data['created_by_id'] = safe_user_id()
                
            # Set currency for each item to UGX
            for item in items_data:
                if 'currency' not in item or item['currency'] != 'UGX':
                    item['currency'] = 'UGX'
            
            # Log the full data we're sending
            logger.info(f"Using direct SQL with: {customer_data} and {len(items_data)} items")
            
            # Call our improved direct SQL implementation
            result, error = direct_create_order(customer_data, items_data, order_type)
            
            if error:
                logger.error(f"Direct SQL order creation failed: {error}")
                return None, error
            
            if result:
                logger.info(f"Direct SQL order created successfully with ID: {result.id}")
                return result, None
            else:
                return None, "Unknown error occurred during direct SQL order creation"
    
    except Exception as e:
        logger.error(f"Error in create_order: {str(e)}")
        
        # Try to rollback stock changes if any were made
        if stock_updates:
            logger.info(f"Attempting to revert {len(stock_updates)} stock updates after error")
            try:
                for update in stock_updates:
                    product = Product.query.get(update['product_id'])
                    if product:
                        # Reset to original stock level
                        product.stock = update['old_stock']
                        db.session.add(product)
                db.session.commit()
            except Exception as rollback_error:
                logger.error(f"Error during stock rollback: {str(rollback_error)}")
        
        return None, str(e)

# Ensure all database operations are committed
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.commit()
    db.session.remove()

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Directly serve JavaScript files to avoid permission issues"""
    logger.info(f"JS file requested: {filename}")
    return send_from_directory(os.path.join(app.static_folder, 'js'), filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Directly serve CSS files to avoid permission issues"""
    logger.info(f"CSS file requested: {filename}")
    return send_from_directory(os.path.join(app.static_folder, 'css'), filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Directly serve image files to avoid permission issues"""
    logger.info(f"Image file requested: {filename}")
    return send_from_directory(os.path.join(app.static_folder, 'images'), filename)

@app.route('/manifest.json')
def manifest():
    """Serve the manifest.json file for PWA functionality"""
    logger.info("Manifest.json requested")
    return send_from_directory(app.static_folder, 'manifest.json')

@app.route('/troubleshoot')
def troubleshoot():
    try:
        return render_template('troubleshoot.html')
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('index'))

def get_order_by_id(order_id):
    """
    Get an order by ID with fallback to direct SQL if SQLAlchemy fails
    """
    try:
        # First try with SQLAlchemy
        order = Order.query.get(order_id)
        if order:
            return order
        # If not found with SQLAlchemy, try direct SQL
        logger.warning(f"Order {order_id} not found with SQLAlchemy, trying direct SQL")
        try:
            conn = sqlite3.connect('instance/pos.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM "order" WHERE id = ?', (order_id,))
            order_row = cursor.fetchone()
            if not order_row:
                conn.close()
                logger.error(f"Order {order_id} not found in direct SQL")
                return None
            order_dict = dict(order_row)
            cursor.execute('''
                SELECT oi.*, p.name as product_name, p.price as product_price 
                FROM order_item oi
                LEFT JOIN product p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            ''', (order_id,))
            items = [dict(row) for row in cursor.fetchall()]
            conn.close()
            # Create a SimpleOrder object to mimic the SQLAlchemy Order
            class SimpleOrder:
                def __init__(self, order_data, item_data):
                    self.id = order_data.get('id')
                    self.reference_number = order_data.get('reference_number', f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{order_data.get('id')}")
                    self.customer_name = order_data.get('customer_name', '')
                    self.customer_phone = order_data.get('customer_phone', '')
                    self.customer_email = order_data.get('customer_email', '')
                    self.customer_address = order_data.get('customer_address', '')
                    self.order_date = order_data.get('order_date', '')
                    self.total_amount = order_data.get('total_amount', 0)
                    self.status = order_data.get('status', 'pending')
                    self.order_type = order_data.get('order_type', 'online')
                    self.viewed = order_data.get('viewed', 0)
                    self.viewed_at = order_data.get('viewed_at')
                    self.completed_at = order_data.get('completed_at')
                    self.updated_at = order_data.get('updated_at')
                    self.created_by_id = order_data.get('created_by_id')
                    self.customer_id = order_data.get('customer_id')
                    self._items = item_data
                @property
                def items(self):
                    class SimpleOrderItem:
                        def __init__(self, item_data):
                            self.id = item_data.get('id', 0)
                            self.order_id = item_data.get('order_id', 0)
                            self.product_id = item_data.get('product_id', 0)
                            self.quantity = item_data.get('quantity', 0)
                            self.price = item_data.get('price', 0)
                            self._product_name = item_data.get('product_name', 'Product')
                            self._product_price = item_data.get('product_price', self.price)
                        @property
                        def subtotal(self):
                            return self.price * self.quantity
                        @property
                        def product(self):
                            class SimpleProduct:
                                def __init__(self, name, price):
                                    self.name = name
                                    self.price = price
                            return SimpleProduct(self._product_name, self._product_price)
                    return [SimpleOrderItem(item) for item in self._items]
            return SimpleOrder(order_dict, items)
        except Exception as inner_e:
            logger.error(f"Error in direct SQL retrieval for order {order_id}: {str(inner_e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Try to return a minimal order object if possible
            try:
                return type('MinimalOrder', (), {'id': order_id, 'items': []})()
            except Exception as fallback_e:
                logger.error(f"Fallback minimal order creation failed: {str(fallback_e)}")
                return None
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for potential future pages and custom error display"""
    logger.warning(f"Unhandled path requested: {path}")
    
    # Try to determine if this is a static file request
    if '.' in path:
        extension = path.split('.')[-1].lower()
        # If it seems to be a static file, try to serve it from static folder
        if extension in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'ico', 'svg', 'woff', 'woff2', 'ttf', 'eot']:
            try:
                # Check if file exists in static folder
                filepath = os.path.join(app.static_folder, path)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    return send_from_directory(app.static_folder, path)
            except Exception as e:
                logger.error(f"Error serving static file {path}: {e}")
                
    # If we reach here, it's not a valid route
    return redirect(url_for('index'))

# Method to identify if user agent is from a mobile or desktop device
def is_mobile():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_agents = ['android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(agent in user_agent for agent in mobile_agents)

# Define common product units 
def get_product_units():
    return [
        # Weight units
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('lb', 'Pound (lb)'),
        ('oz', 'Ounce (oz)'),
        
        # Volume units
        ('l', 'Liter (l)'),
        ('ml', 'Milliliter (ml)'),
        ('gal', 'Gallon (gal)'),
        ('qt', 'Quart (qt)'),
        ('pt', 'Pint (pt)'),
        ('fl_oz', 'Fluid Ounce (fl oz)'),
        ('cup', 'Cup'),
        ('tbsp', 'Tablespoon (tbsp)'),
        ('tsp', 'Teaspoon (tsp)'),
        
        # Count units
        ('pcs', 'Pieces (pcs)'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('bag', 'Bag'),
        ('carton', 'Carton'),
        ('bottle', 'Bottle'),
        ('jar', 'Jar'),
        ('can', 'Can'),
        ('bundle', 'Bundle'),
        ('roll', 'Roll'),
        ('case', 'Case'),
        ('tray', 'Tray'),
        ('crate', 'Crate'),
        ('pallet', 'Pallet'),
        
        # Length units
        ('m', 'Meter (m)'),
        ('cm', 'Centimeter (cm)'),
        ('in', 'Inch (in)'),
        ('ft', 'Foot (ft)'),
        ('yd', 'Yard (yd)'),
        
        # Area units
        ('sqm', 'Square meter (m²)'),
        ('sqft', 'Square foot (ft²)'),
        
        # Other common units
        ('pair', 'Pair'),
        ('dozen', 'Dozen'),
        ('half_dozen', 'Half Dozen'),
        ('set', 'Set'),
        ('unit', 'Unit'),
        ('bunch', 'Bunch'),
        ('head', 'Head'),
        ('stalk', 'Stalk'),
        ('slice', 'Slice'),
        ('loaf', 'Loaf'),
        ('clove', 'Clove')
    ]

# Define currency options for the application
def get_currencies():
    return [
        # Major world currencies
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('JPY', 'Japanese Yen (¥)'),
        ('CNY', 'Chinese Yuan (¥)'),
        ('INR', 'Indian Rupee (₹)'),
        ('AUD', 'Australian Dollar (A$)'),
        ('CAD', 'Canadian Dollar (C$)'),
        ('CHF', 'Swiss Franc (Fr)'),
        ('HKD', 'Hong Kong Dollar (HK$)'),
        
        # African currencies
        ('UGX', 'Ugandan Shilling (USh)'),
        ('KES', 'Kenyan Shilling (KSh)'),
        ('TZS', 'Tanzanian Shilling (TSh)'),
        ('RWF', 'Rwandan Franc (RF)'),
        ('NGN', 'Nigerian Naira (₦)'),
        ('ZAR', 'South African Rand (R)'),
        ('EGP', 'Egyptian Pound (E£)'),
        ('GHS', 'Ghanaian Cedi (₵)'),
        ('MAD', 'Moroccan Dirham (MAD)'),
        ('XOF', 'West African CFA Franc (CFA)'),
        ('XAF', 'Central African CFA Franc (FCFA)'),
        
        # Middle Eastern currencies
        ('AED', 'UAE Dirham (د.إ)'),
        ('SAR', 'Saudi Riyal (﷼)'),
        ('QAR', 'Qatari Riyal (﷼)'),
        ('ILS', 'Israeli Shekel (₪)'),
        ('TRY', 'Turkish Lira (₺)'),
        
        # Asian currencies
        ('KRW', 'South Korean Won (₩)'),
        ('SGD', 'Singapore Dollar (S$)'),
        ('THB', 'Thai Baht (฿)'),
        ('IDR', 'Indonesian Rupiah (Rp)'),
        ('MYR', 'Malaysian Ringgit (RM)'),
        ('PHP', 'Philippine Peso (₱)'),
        ('VND', 'Vietnamese Dong (₫)'),
        ('BDT', 'Bangladeshi Taka (৳)'),
        ('PKR', 'Pakistani Rupee (₨)'),
        
        # European currencies
        ('RUB', 'Russian Ruble (₽)'),
        ('PLN', 'Polish Złoty (zł)'),
        ('SEK', 'Swedish Krona (kr)'),
        ('NOK', 'Norwegian Krone (kr)'),
        ('DKK', 'Danish Krone (kr)'),
        ('CZK', 'Czech Koruna (Kč)'),
        ('HUF', 'Hungarian Forint (Ft)'),
        ('RON', 'Romanian Leu (lei)'),
        
        # American currencies
        ('MXN', 'Mexican Peso (Mex$)'),
        ('BRL', 'Brazilian Real (R$)'),
        ('ARS', 'Argentine Peso ($)'),
        ('CLP', 'Chilean Peso (CLP$)'),
        ('COP', 'Colombian Peso (COL$)'),
        ('PEN', 'Peruvian Sol (S/)'),
        
        # Oceanian currencies
        ('NZD', 'New Zealand Dollar (NZ$)'),
        ('FJD', 'Fijian Dollar (FJ$)'),
        
        # Cryptocurrencies
        ('BTC', 'Bitcoin (₿)'),
        ('ETH', 'Ethereum (Ξ)'),
        ('XRP', 'Ripple (XRP)'),
        ('LTC', 'Litecoin (Ł)'),
        ('USDT', 'Tether (₮)')
    ]

# Define grocery categories and common items
def get_grocery_categories():
    return [
        # Produce
        ('produce', 'Produce', [
            ('fresh_fruits', 'Fresh Fruits'),
            ('fresh_vegetables', 'Fresh Vegetables'),
            ('herbs', 'Fresh Herbs'),
            ('packaged_produce', 'Packaged Produce'),
            ('organic_produce', 'Organic Produce'),
            ('salad_kits', 'Salad Kits')
        ]),
        
        # Meat & Seafood
        ('meat_seafood', 'Meat & Seafood', [
            ('beef', 'Beef'),
            ('pork', 'Pork'),
            ('poultry', 'Poultry'),
            ('fish', 'Fish'),
            ('shellfish', 'Shellfish'),
            ('deli_meats', 'Deli Meats'),
            ('sausages', 'Sausages'),
            ('meat_alternatives', 'Meat Alternatives')
        ]),
        
        # Dairy & Eggs
        ('dairy_eggs', 'Dairy & Eggs', [
            ('milk', 'Milk'),
            ('cheese', 'Cheese'),
            ('eggs', 'Eggs'),
            ('yogurt', 'Yogurt'),
            ('butter', 'Butter & Margarine'),
            ('cream', 'Cream'),
            ('dairy_alternatives', 'Dairy Alternatives')
        ]),
        
        # Bakery
        ('bakery', 'Bakery', [
            ('bread', 'Bread'),
            ('rolls_buns', 'Rolls & Buns'),
            ('cakes', 'Cakes & Pastries'),
            ('cookies', 'Cookies'),
            ('pies', 'Pies'),
            ('bakery_desserts', 'Bakery Desserts'),
            ('tortillas', 'Tortillas & Flatbreads')
        ]),
        
        # Pantry Staples
        ('pantry', 'Pantry Staples', [
            ('rice_grains', 'Rice & Grains'),
            ('pasta', 'Pasta & Noodles'),
            ('canned_goods', 'Canned Goods'),
            ('soups', 'Soups & Broths'),
            ('beans_legumes', 'Beans & Legumes'),
            ('baking', 'Baking Ingredients'),
            ('condiments', 'Condiments & Sauces'),
            ('oils_vinegars', 'Oils & Vinegars'),
            ('spices_seasonings', 'Spices & Seasonings'),
            ('sweeteners', 'Sweeteners & Syrups')
        ]),
        
        # Snacks & Confectionery
        ('snacks', 'Snacks & Confectionery', [
            ('chips', 'Chips & Crisps'),
            ('crackers', 'Crackers'),
            ('nuts_seeds', 'Nuts & Seeds'),
            ('dried_fruits', 'Dried Fruits'),
            ('chocolate', 'Chocolate'),
            ('candy', 'Candy & Sweets'),
            ('energy_bars', 'Energy & Protein Bars'),
            ('popcorn', 'Popcorn & Puffed Snacks')
        ]),
        
        # Beverages
        ('beverages', 'Beverages', [
            ('water', 'Water'),
            ('soda', 'Soda & Soft Drinks'),
            ('juice', 'Juices'),
            ('coffee', 'Coffee'),
            ('tea', 'Tea'),
            ('sports_drinks', 'Sports & Energy Drinks'),
            ('drink_mixes', 'Drink Mixes & Powders'),
            ('non_alcoholic', 'Non-Alcoholic Beverages')
        ]),
        
        # Frozen Foods
        ('frozen', 'Frozen Foods', [
            ('frozen_vegetables', 'Frozen Vegetables'),
            ('frozen_fruits', 'Frozen Fruits'),
            ('frozen_meals', 'Frozen Meals'),
            ('frozen_pizza', 'Frozen Pizza'),
            ('ice_cream', 'Ice Cream & Frozen Desserts'),
            ('frozen_breakfast', 'Frozen Breakfast Items'),
            ('frozen_meat_seafood', 'Frozen Meat & Seafood')
        ])
    ]

# Define specific grocery items by category for inventory management with detailed information
def get_grocery_items():
    return {
        # Fresh Fruits
        'fresh_fruits': [
            {'name': 'Apples', 'description': 'Fresh, crisp apples', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Bananas', 'description': 'Ripe yellow bananas', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Oranges', 'description': 'Juicy seedless oranges', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Grapes', 'description': 'Sweet seedless grapes', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_fruits'}
        ],
        
        # Fresh Vegetables
        'fresh_vegetables': [
            {'name': 'Lettuce', 'description': 'Fresh green lettuce', 'unit': 'head', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Spinach', 'description': 'Organic baby spinach', 'unit': 'bag', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Tomatoes', 'description': 'Ripe red tomatoes', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Onions', 'description': 'Fresh yellow onions', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'}
        ],
        
        # Dairy & Eggs
        'dairy_eggs': [
            {'name': 'Milk', 'description': 'Fresh whole milk', 'unit': 'l', 'category_group': 'dairy_eggs', 'category': 'milk'},
            {'name': 'Eggs', 'description': 'Large fresh eggs', 'unit': 'dozen', 'category_group': 'dairy_eggs', 'category': 'eggs'},
            {'name': 'Cheddar', 'description': 'Sharp cheddar cheese', 'unit': 'kg', 'category_group': 'dairy_eggs', 'category': 'cheese'}
        ],
        
        # Beverages
        'beverages': [
            {'name': 'Water', 'description': 'Bottled mineral water', 'unit': 'bottle', 'category_group': 'beverages', 'category': 'water'},
            {'name': 'Orange Juice', 'description': 'Fresh squeezed orange juice', 'unit': 'l', 'category_group': 'beverages', 'category': 'juice'},
            {'name': 'Coffee', 'description': 'Ground coffee beans', 'unit': 'bag', 'category_group': 'beverages', 'category': 'coffee'},
            {'name': 'Tea', 'description': 'Black tea bags', 'unit': 'box', 'category_group': 'beverages', 'category': 'tea'}
        ]
    }

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add location columns if they don't exist
        try:
            with db.engine.connect() as conn:
                # Check if columns exist
                result = conn.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                # Add missing columns
                if 'latitude' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN latitude FLOAT"))
                if 'longitude' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN longitude FLOAT"))
                if 'location_name' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN location_name VARCHAR(200)"))
                if 'last_location_update' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN last_location_update DATETIME"))
                
                conn.commit()
        except Exception as e:
            app.logger.error(f"Error adding location columns: {e}")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True,
                is_staff=True,
                full_name='System Administrator',
                initials='SA'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Admin user created successfully")
        
        app.logger.info("Database tables created successfully")

def check_db_integrity():
    """
    Check database integrity and repair issues if needed
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        if integrity_result != "ok":
            logger.critical(f"Database integrity check failed: {integrity_result}")
            
            # Backup the database
            import shutil
            from datetime import datetime
            backup_file = f"instance/pos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                shutil.copy2('instance/pos.db', backup_file)
                logger.info(f"Created database backup at {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to create database backup: {str(backup_error)}")
            
            # Try to fix common issues
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                logger.error(f"Foreign key violations found: {fk_violations}")
            
            # Check for incorrect stock movements
            cursor.execute("""
            SELECT p.id, p.name, p.stock, 
                   (SELECT SUM(sm.quantity) FROM stock_movement sm 
                    WHERE sm.product_id = p.id AND sm.movement_type = 'restock') as total_restock,
                   (SELECT SUM(sm.quantity) FROM stock_movement sm 
                    WHERE sm.product_id = p.id AND sm.movement_type = 'sale') as total_sales
            FROM product p
            """)
            
            stock_discrepancies = []
            for row in cursor.fetchall():
                product_id, name, current_stock, total_restock, total_sales = row
                total_restock = total_restock or 0
                total_sales = total_sales or 0
                expected_stock = total_restock - total_sales
                
                if abs(current_stock - expected_stock) > 0.001:  # Allow small float rounding errors
                    stock_discrepancies.append({
                        'product_id': product_id,
                        'name': name,
                        'current_stock': current_stock,
                        'expected_stock': expected_stock,
                        'difference': current_stock - expected_stock
                    })
            
            if stock_discrepancies:
                logger.warning(f"Found {len(stock_discrepancies)} stock discrepancies")
                for discrepancy in stock_discrepancies:
                    logger.warning(f"Stock discrepancy for {discrepancy['name']}: current={discrepancy['current_stock']}, expected={discrepancy['expected_stock']}")
        else:
            logger.info("Database integrity check passed")
        
        conn.close()
        return True
    except Exception as e:
        logger.critical(f"Error checking database integrity: {str(e)}")
        return False

@app.route('/api/test', methods=['GET'])
def api_test():
    """Simple test endpoint to check if API routing is working"""
    return jsonify({
        'success': True,
        'message': 'API endpoint is working',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/my_sales')
@login_required
@staff_required
def my_sales():
    """Redirect to staff_orders since my_sales was removed"""
    return redirect(url_for('staff_orders'))

@app.route('/my_sales/order/<int:order_id>')
@login_required
@staff_required
def my_sales_order_detail(order_id):
    """Redirect to staff_order_detail since my_sales was removed"""
    return redirect(url_for('staff_order_detail', order_id=order_id))

@app.route('/api/admin_stats')
@login_required
@admin_required
def api_admin_stats():
    """Return aggregated statistics for the admin dashboard (sales overview, product counts, etc.)."""
    try:
        db_path = 'instance/pos.db'
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # -----------------------------------------
        # 1. Today\'s total sales (completed orders)
        # -----------------------------------------
        cursor.execute("""
            SELECT IFNULL(SUM(total_amount), 0) AS today_sales
            FROM "order"
            WHERE DATE(order_date) = DATE('now', 'localtime')
              AND status != 'cancelled'
        """)
        today_sales = cursor.fetchone()['today_sales'] or 0

        # -------------------------------------------------
        # 2. Total products / low-stock / out-of-stock count
        # -------------------------------------------------
        cursor.execute("SELECT COUNT(*) AS total_products FROM product")
        total_products = cursor.fetchone()['total_products']

        cursor.execute("""
            SELECT COUNT(*) AS low_stock
            FROM product
            WHERE stock <= reorder_point AND stock > 0
        """)
        low_stock_products = cursor.fetchone()['low_stock']

        cursor.execute("SELECT COUNT(*) AS out_of_stock FROM product WHERE stock <= 0")
        out_of_stock_products = cursor.fetchone()['out_of_stock']

        # -------------------------------------------------
        # 3. Daily sales (last 7 days) for chart
        # -------------------------------------------------
        cursor.execute("""
            SELECT DATE(order_date) AS order_day, IFNULL(SUM(total_amount), 0) AS total
            FROM "order"
            WHERE DATE(order_date) >= DATE('now', '-6 days', 'localtime')
              AND status != 'cancelled'
            GROUP BY order_day
            ORDER BY order_day
        """)
        rows = cursor.fetchall()
        # Build lists for the chart; ensure all days present
        from datetime import datetime, timedelta
        dates = []
        sales_data = []
        for i in range(7):
            day = (datetime.now() - timedelta(days=6 - i)).date()
            dates.append(day.strftime('%Y-%m-%d'))
            # find matching row
            match = next((r['total'] for r in rows if r['order_day'] == day.strftime('%Y-%m-%d')), 0)
            sales_data.append(match or 0)

        conn.close()

        return jsonify({
            'success': True,
            'today_sales': today_sales,
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
            'dates': dates,
            'sales_data': sales_data
        })
    except Exception as e:
        logger.error(f"Error in api_admin_stats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stock_movements')
@login_required
@admin_required
def api_stock_movements():
    """Return recent stock movements for the dashboard table."""
    try:
        db_path = 'instance/pos.db'
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sm.id, sm.product_id, sm.quantity, sm.movement_type, sm.remaining_stock, sm.timestamp,
                   p.name AS product_name, p.unit
            FROM stock_movement sm
            JOIN product p ON p.id = sm.product_id
            ORDER BY sm.timestamp DESC
            LIMIT 20
        """)
        rows = cursor.fetchall()

        movements = []
        for r in rows:
            movements.append({
                'id': r['id'],
                'product_id': r['product_id'],
                'product_name': r['product_name'],
                'movement_type': r['movement_type'],
                'quantity': r['quantity'],
                'unit': r['unit'],
                'remaining_stock': r['remaining_stock'],
                'timestamp': r['timestamp']
            })
        conn.close()
        return jsonify({'success': True, 'movements': movements})
    except Exception as e:
        logger.error(f"Error in api_stock_movements: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/products')
@login_required
@admin_required
def api_products():
    """Return product list with live stock info for dashboard management table."""
    try:
        db_path = 'instance/pos.db'
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, price, stock, reorder_point, max_stock, unit, category
            FROM product
        """)
        rows = cursor.fetchall()

        products = {}
        for r in rows:
            # Determine stock status
            if r['stock'] <= 0:
                status = 'out'
            elif r['stock'] < r['reorder_point']:
                status = 'low'
            elif r['max_stock'] and r['stock'] > r['max_stock']:
                status = 'high'
            else:
                status = 'normal'

            products[str(r['id'])] = {
                'name': r['name'],
                'price': r['price'],
                'stock': r['stock'],
                'unit': r['unit'],
                'category': r['category'],
                'stock_status': status
            }
        conn.close()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        logger.error(f"Error in api_products: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff_orders')
@login_required
@staff_required
def api_staff_orders():
    """Return a JSON list of orders for the staff dashboard with optional filters."""
    try:
        status = request.args.get('status', '')
        order_type = request.args.get('order_type', '')
        limit = int(request.args.get('limit', 50))

        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        # Build base query
        query = "SELECT id, order_date, customer_name, order_type, status, total_amount FROM \"order\""
        params = []
        conditions = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if order_type:
            conditions.append("order_type = ?")
            params.append(order_type)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY order_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        orders = []
        for row in rows:
            orders.append({
                'id': row[0],
                'order_date': row[1],
                'customer_name': row[2] or 'Anonymous Customer',
                'order_type': row[3],
                'status': row[4],
                'total_amount': float(row[5])
            })

        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        logger.error(f"Error in api_staff_orders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Alias route for legacy templates that still reference 'all_staff_orders'
@app.route('/staff/all-orders')
@login_required
@staff_required
def all_staff_orders():
    """Legacy endpoint kept for backward-compatibility – delegates to staff_orders."""
    return staff_orders()

def parse_any_datetime(dt_str):
    from datetime import datetime
    if not isinstance(dt_str, str):
        return dt_str
    try:
        # Try ISO 8601 first
        return datetime.fromisoformat(dt_str)
    except Exception:
        pass
    try:
        # Try SQL format
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        pass
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return dt_str  # fallback to original

# Add a Jinja filter to convert UTC to Africa/Kampala local time
@app.template_filter('localtime')
def localtime_filter(value, fmt='%Y-%m-%d %H:%M:%S'):
    if not value:
        return ''
    from datetime import datetime
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
            except Exception:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=pytz.UTC)
    kampala = pytz.timezone('Africa/Kampala')
    local_dt = value.astimezone(kampala)
    return local_dt.strftime(fmt)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'rent', 'utilities', 'salaries', 'other'
    date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    created_by = db.relationship('User', backref=db.backref('expenses', passive_deletes=True))

    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_expenses():
    if request.method == 'POST':
        try:
            description = request.form.get('description')
            amount = float(request.form.get('amount', 0))
            category = request.form.get('category')
            notes = request.form.get('notes')
            
            if not description or not amount or not category:
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('manage_expenses'))
            
            expense = Expense(
                description=description,
                amount=amount,
                category=category,
                notes=notes,
                created_by_id=safe_user_id() if current_user.is_authenticated else None
            )
            
            db.session.add(expense)
            db.session.commit()
            
            flash('Expense added successfully', 'success')
            return redirect(url_for('manage_expenses'))
            
        except Exception as e:
            logger.error(f'Error adding expense: {str(e)}')
            flash('Error adding expense', 'error')
            return redirect(url_for('manage_expenses'))
    
    # GET request - show expenses page
    try:
        # Get date range parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD format.', 'error')
                return redirect(url_for('manage_expenses'))
        else:
            # Default to current month
            today = datetime.now().date()
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Get expenses for the date range
        expenses = Expense.query.filter(
            db.func.date(Expense.date) >= start_date,
            db.func.date(Expense.date) <= end_date
        ).order_by(Expense.date.desc()).all()
        
        # Calculate total expenses
        total_expenses = sum(expense.amount for expense in expenses)
        
        # Get expenses by category
        expenses_by_category = {}
        for expense in expenses:
            if expense.category not in expenses_by_category:
                expenses_by_category[expense.category] = 0
            expenses_by_category[expense.category] += expense.amount
        
        currency = 'UGX'  # Define currency before passing to template
        return render_template(
            'expenses.html',
            expenses=expenses,
            total_expenses=total_expenses,
            expenses_by_category=expenses_by_category,
            start_date=start_date,
            end_date=end_date,
            currency=currency
        )
        
    except Exception as e:
        logger.error(f'Error loading expenses page: {str(e)}')
        flash('Error loading expenses page', 'error')
        return redirect(url_for('admin'))

@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
@admin_required
def delete_expense(expense_id):
    try:
        expense = Expense.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully', 'success')
    except Exception as e:
        logger.error(f'Error deleting expense: {str(e)}')
        flash('Error deleting expense', 'error')
    return redirect(url_for('manage_expenses'))

@app.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    if request.method == 'POST':
        try:
            expense.description = request.form.get('description')
            expense.amount = float(request.form.get('amount', 0))
            expense.category = request.form.get('category')
            expense.notes = request.form.get('notes')
            
            if not expense.description or not expense.amount or not expense.category:
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('edit_expense', expense_id=expense_id))
            
            db.session.commit()
            flash('Expense updated successfully', 'success')
            return redirect(url_for('manage_expenses'))
            
        except Exception as e:
            logger.error(f'Error updating expense: {str(e)}')
            flash('Error updating expense', 'error')
            return redirect(url_for('edit_expense', expense_id=expense_id))
    
    return render_template('edit_expense.html', expense=expense)

# Add this new route for admin monitoring
@app.route('/admin/monitor_staff', methods=['GET'])
@login_required
@admin_required
def monitor_staff():
    from datetime import datetime, timedelta, timezone
    def generate_initials(full_name):
        if not full_name:
            return ''
        words = full_name.split()
        return ''.join(word[0].upper() for word in words[:4])
    active_staff = User.query.filter_by(is_staff=True).all()
    active_sessions = []
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    for staff in active_staff:
        last_order = Order.query.filter_by(created_by_id=staff.id).order_by(Order.order_date.desc()).first()
        is_active = staff.last_seen and (now - (staff.last_seen.replace(tzinfo=timezone.utc) if staff.last_seen.tzinfo is None else staff.last_seen)) < timedelta(minutes=5)
        initials = staff.initials or generate_initials(staff.full_name)
        last_seen_utc = None
        if staff.last_seen:
            dt = staff.last_seen
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            last_seen_utc = dt.astimezone(timezone.utc).isoformat()
        session_data = {
            'staff_id': staff.id,
            'username': staff.username,
            'full_name': staff.full_name,
            'initials': initials,
            'email': staff.email,
            'last_seen': last_seen_utc,
            'is_active': is_active,
            'last_activity': last_order.order_date if last_order else None,
            'current_sale': {
                'order_id': last_order.id if last_order else None,
                'total_amount': last_order.total_amount if last_order else 0,
                'items_count': len(last_order.items) if last_order else 0
            } if last_order else None
        }
        active_sessions.append(session_data)
    return jsonify({'success': True, 'active_staff': active_sessions})

# Add this new route to get real-time staff activity
@app.route('/admin/staff_activity/<int:staff_id>', methods=['GET'])
@login_required
@admin_required
def staff_activity(staff_id):
    staff = User.query.get_or_404(staff_id)
    
    # Get all orders for this staff member (by created_by_id)
    orders_by_creator = Order.query.filter_by(created_by_id=staff_id).all()
    
    # Optionally, also include orders where initials or email match (if those fields exist)
    # This is a fallback for legacy data
    extra_orders = []
    if hasattr(Order, 'customer_email') and staff.email:
        extra_orders = Order.query.filter(Order.customer_email == staff.email).all()
    elif hasattr(Order, 'customer_name') and staff.full_name:
        extra_orders = Order.query.filter(Order.customer_name == staff.full_name).all()
    
    # Combine and deduplicate orders
    all_orders = {order.id: order for order in orders_by_creator}
    for order in extra_orders:
        all_orders[order.id] = order
    recent_orders = sorted(all_orders.values(), key=lambda o: o.order_date, reverse=True)
    
    orders_data = []
    for order in recent_orders:
        order_data = {
            'id': order.id,
            'reference_number': order.reference_number,
            'total_amount': order.total_amount,
            'created_at': order.order_date.isoformat() if hasattr(order, 'order_date') and order.order_date else None,
            'items': [{
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.price
            } for item in order.items]
        }
        orders_data.append(order_data)
    
    return jsonify({
        'success': True,
        'staff': {
            'id': staff.id,
            'full_name': staff.full_name,
            'initials': staff.initials,
            'email': staff.email
        },
        'recent_orders': orders_data,
        'has_activity': bool(orders_data)
    })

# Add this new route for admin to start monitoring a staff member
@app.route('/admin/start_monitoring/<int:staff_id>', methods=['POST'])
@login_required
@admin_required
def start_monitoring(staff_id):
    staff = User.query.get_or_404(staff_id)
    if not staff.is_staff:
        return jsonify({'success': False, 'error': 'User is not a staff member'})
    
    # Store the admin's monitoring session
    session['admin_monitoring_id'] = safe_user_id() if current_user.is_authenticated else None
    session['monitored_staff_id'] = staff_id
    
    return jsonify({
        'success': True,
        'message': f'Now monitoring {staff.full_name}'
    })

# Add this new route for admin to stop monitoring
@app.route('/admin/stop_monitoring', methods=['POST'])
@login_required
@admin_required
def stop_monitoring():
    session.pop('admin_monitoring_id', None)
    session.pop('monitored_staff_id', None)
    return jsonify({'success': True, 'message': 'Stopped monitoring'})

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        from datetime import datetime
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        print(f"Updated last_seen for {current_user.username} at {current_user.last_seen}")

@app.route('/admin/monitor')
@login_required
@admin_required
def admin_monitor():
    return render_template('admin_monitor.html')

# Flask-Mail configuration (sample, replace with your SMTP details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'givenwholesalers1@gmail.com'
app.config['MAIL_PASSWORD'] = 'vlcrxbmbmfntfjia'  # Replace with your new app password
app.config['MAIL_DEFAULT_SENDER'] = 'givenwholesalers1@gmail.com'

mail = Mail(app)

def send_email(subject, recipients, body, html=None):
    try:
        msg = Message(subject, recipients=recipients, body=body, html=html)
        mail.send(msg)
        app.logger.info(f"Email sent to {recipients} with subject '{subject}'")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")
        return False

@app.route('/test_email')
def test_email():
    try:
        msg = Message('Test Email from POS System',
                      sender=app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[app.config['MAIL_DEFAULT_SENDER']])
        msg.body = """
        Hello!

        Thank you for using our system. We appreciate your trust and hope you find it helpful for your business.

        Best regards,
        Your POS System Team
        """
        mail.send(msg)
        return 'Test email sent successfully!'
    except Exception as e:
        return f'Failed to send test email: {str(e)}'

def safe_user_id():
    from flask_login import current_user
    return current_user.id if getattr(current_user, 'is_authenticated', False) else None

@app.route('/api/update_location', methods=['POST'])
@login_required
def update_location():
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location_name = data.get('location_name')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Missing location data'}), 400
            
        current_user.latitude = latitude
        current_user.longitude = longitude
        current_user.location_name = location_name
        current_user.last_location_update = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error updating location: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/staff_locations')
@login_required
def get_staff_locations():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    staff = User.query.filter_by(is_staff=True).all()
    locations = []
    
    for user in staff:
        locations.append({
            'id': user.id,
            'username': user.username,
            'latitude': user.latitude,
            'longitude': user.longitude,
            'location_name': user.location_name,
            'last_location_update': user.last_location_update.strftime('%Y-%m-%d %H:%M:%S') if user.last_location_update else None
        })
    
    return jsonify({
        'success': True,
        'locations': locations
    })

# Add a placeholder for staff_orders if not defined
@app.route('/staff_orders')
@login_required
@staff_required
def staff_orders():
    try:
        # Get URL parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of orders per page
        
        # Get filter parameters
        status_filter = request.args.get('status', 'current')
        order_type_filter = request.args.get('order_type', '')
        
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause for filters
        where_clauses = []
        params = []
        
        if status_filter and status_filter != 'current':
            where_clauses.append("status = ?")
            params.append(status_filter)
        elif status_filter == 'current':
            where_clauses.append("status IN ('pending', 'processing')")
        
        if order_type_filter:
            where_clauses.append("order_type = ?")
            params.append(order_type_filter)
        
        # Construct the WHERE clause
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Count total orders for pagination
        count_query = f"""
            SELECT COUNT(*)
            FROM "order"
            {where_sql}
        """
        
        cursor.execute(count_query, params)
        total_orders = cursor.fetchone()[0]
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get paginated orders
        orders_query = f"""
            SELECT id, customer_name, order_date, total_amount, status,
                   order_type, viewed, created_by_id
            FROM "order"
            {where_sql}
            ORDER BY order_date DESC
            LIMIT ? OFFSET ?
        """
        
        # Add pagination parameters to the end of params list
        query_params = params + [per_page, offset]
        cursor.execute(orders_query, query_params)
        
        order_data = cursor.fetchall()
        
        # Get staff names for created_by_id
        staff_dict = {}
        staff_ids = [row[7] for row in order_data if row[7] is not None]
        if staff_ids:
            placeholders = ','.join(['?'] * len(staff_ids))
            cursor.execute(f"SELECT id, username FROM user WHERE id IN ({placeholders})", staff_ids)
            for staff_id, username in cursor.fetchall():
                staff_dict[staff_id] = username
        
        # Create a list of SimpleNamespace objects to mimic ORM
        orders = []
        for order_row in order_data:
            # Convert string date to datetime if needed
            order_date = order_row[2]
            if isinstance(order_date, str):
                try:
                    order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # If conversion fails, use current time as fallback
                    order_date = datetime.utcnow()
            
            # Get staff name
            created_by_id = order_row[7]
            created_by = staff_dict.get(created_by_id, 'System') if created_by_id else 'System'
            
            order = SimpleNamespace(
                id=order_row[0],
                customer_name=order_row[1],
                order_date=order_date,
                total_amount=order_row[3],
                status=order_row[4],
                order_type=order_row[5],
                viewed=order_row[6],
                created_by=created_by
            )
            orders.append(order)
        
        # Calculate total pages for pagination
        total_pages = (total_orders + per_page - 1) // per_page
        
        conn.close()
        
        # Get available statuses for filtering
        statuses = ['pending', 'processing', 'completed', 'cancelled']
        order_types = ['online', 'in-store']
        
        return render_template('staff/orders.html', 
                              orders=orders, 
                              page=page, 
                              total_pages=total_pages,
                              status_filter=status_filter,
                              order_type_filter=order_type_filter,
                              statuses=statuses,
                              order_types=order_types)
    except Exception as e:
        logger.error(f"Error in staff_orders: {str(e)}")
        flash(f"Error loading orders: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/staff/order/<int:order_id>')
@login_required
@staff_required
def staff_order_detail(order_id):
    """Show detailed information for a specific order (staff view)"""
    try:
        # Use direct SQL instead of ORM to avoid column issues
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        # Check if payment columns exist
        cursor.execute("PRAGMA table_info('order')")
        columns = [col[1] for col in cursor.fetchall()]
        has_payment_columns = 'payment_method' in columns and 'payment_status' in columns
        has_payment_id = 'payment_id' in columns

        # Get the order details
        base_query = """
            SELECT id, customer_id, order_date, total_amount, status, 
                   customer_name, customer_phone, customer_email, customer_address,
                   order_type, created_by_id, updated_at, completed_at, viewed, viewed_at, payment_status, payment_method
        """

        if has_payment_columns and has_payment_id:
            base_query += ", payment_method, payment_status, payment_id"

        query = base_query + " FROM \"order\" WHERE id = ?"

        cursor.execute(query, (order_id,))

        order_data = cursor.fetchone()

        if not order_data:
            flash('Order not found', 'error')
            return redirect(url_for('my_sales'))

        # Check if this order belongs to the current staff member
        if order_data[10] != current_user.id:  # created_by_id index
            flash('You do not have permission to view this order.', 'danger')
            return redirect(url_for('my_sales'))

        # Mark order as viewed when opened
        if order_data[13] == 0 or not order_data[13]:  # viewed column index
            try:
                cursor.execute(
                    'UPDATE "order" SET viewed = 1, viewed_at = ? WHERE id = ?', 
                    (datetime.utcnow().isoformat(), order_id)
                )
                conn.commit()
                app.logger.info(f"Order #{order_id} marked as viewed from staff_orders")
            except Exception as e:
                app.logger.error(f"Error marking order as viewed: {str(e)}")
                # Continue even if marking fails

        # Get order items
        cursor.execute("""
            SELECT oi.id, oi.product_id, oi.quantity, oi.price, p.name
            FROM order_item oi
            JOIN product p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))

        order_items = cursor.fetchall()

        # Create a simple object to pass to the template that mimics the ORM object
        order_dict = {
            'id': order_data[0],
            'customer_id': order_data[1],
            'order_date': order_data[2],
            'total_amount': order_data[3],
            'status': order_data[4],
            'customer_name': order_data[5],
            'customer_phone': order_data[6],
            'customer_email': order_data[7],
            'customer_address': order_data[8],
            'order_type': order_data[9],
            'created_by_id': order_data[10],
            'updated_at': order_data[11],
            'completed_at': order_data[12],
            'viewed': order_data[13],
            'viewed_at': order_data[14],
            'payment_status': order_data[15],
            'payment_method': order_data[16]
        }

        # Add payment fields if they exist
        if has_payment_columns and has_payment_id and len(order_data) >= 18:
            order_dict['payment_method'] = order_data[17]
            order_dict['payment_status'] = order_data[18]
            order_dict['payment_id'] = order_data[19]
        else:
            # Provide default values
            order_dict['payment_method'] = 'Cash'
            order_dict['payment_status'] = 'paid' if order_data[4] == 'completed' else 'pending'
            order_dict['payment_id'] = None

        from types import SimpleNamespace
        order = SimpleNamespace(**order_dict)

        # Create SimpleNamespace objects for order items
        items = []
        for item_data in order_items:
            item = SimpleNamespace(
                id=item_data[0],
                product_id=item_data[1],
                quantity=item_data[2],
                price=item_data[3],
                subtotal=item_data[2] * item_data[3],
                product=SimpleNamespace(
                    name=item_data[4]
                )
            )
            items.append(item)

        # Add items to the order
        order.items = items

        conn.close()

        # Pass tax rate for calculations
        tax_rate = 0.18  # 18% VAT

        return render_template('staff/order_detail.html', 
                              order=order,
                              tax_rate=tax_rate,
                              staff_update_order_status_url=url_for('staff_update_order_status', order_id=order.id))
    except Exception as e:
        flash('Error loading order details: ' + str(e), 'danger')
        app.logger.error(f"Error in staff_order_detail: {str(e)}")
        return redirect(url_for('my_sales'))

@app.route('/get_cart_count')
def get_cart_count():
    """Get the current cart item count for AJAX requests"""
    try:
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=current_user.id, status='active').first()
        else:
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        count = 0
        if cart:
            # Sum up all items in the cart
            items = CartItem.query.filter_by(cart_id=cart.id).all()
            count = sum(item.quantity for item in items)

        return jsonify({'success': True, 'count': count})
    except Exception as e:
        app.logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'success': False, 'error': str(e), 'count': 0})

@app.route('/api/stock_status')
def api_stock_status():
    """API endpoint to get current stock status for products."""
    try:
        products = Product.query.all()
        result = {}
        for product in products:
            result[product.id] = {
                'name': product.name,
                'stock': product.stock,
                'unit': product.unit,
                'category': product.category,
                'stock_status': product.stock_status,
                'max_stock': product.max_stock,
                'reorder_point': product.reorder_point,
                'stock_percentage': product.stock_percentage,
                'low_stock_threshold': product.low_stock_threshold,
                'needs_restock': product.stock <= product.reorder_point,
                'is_overstocked': product.stock >= product.max_stock * 0.9
            }
        return jsonify({'success': True, 'products': result})
    except Exception as e:
        app.logger.error(f"Error in /api/stock_status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/staff/update_order_status/<int:order_id>', methods=['POST'])
@login_required
@staff_required
def staff_update_order_status(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get('status')
        notes = request.form.get('notes', '')
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('staff_order_detail', order_id=order_id))
        old_status = order.status
        order.status = new_status
        now = datetime.utcnow()
        order.updated_at = now
        if new_status == 'completed' and old_status != 'completed':
            order.completed_at = now
        db.session.commit()
        flash(f'Order status updated to {new_status}', 'success')
        return redirect(url_for('staff_order_detail', order_id=order_id))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating order status: {str(e)}")
        flash(f"Error updating order: {str(e)}", "error")
        return redirect(url_for('staff_order_detail', order_id=order_id))

socketio = SocketIO(app)

@socketio.on('ping_last_seen')
def handle_ping_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        # Optionally, broadcast update to admin dashboard
        emit('last_seen_update', {
            'user_id': current_user.id,
            'last_seen': current_user.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

if __name__ == '__main__':
    # Initialize database and create all tables
    init_db()
    
    # Check database integrity
    check_db_integrity()
    
    # Run app with permissive host to allow access from all IPs in local network
    # This can help with network-related 403 errors
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 