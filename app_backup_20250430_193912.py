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
from datetime import datetime, timedelta, date
from types import SimpleNamespace
from flask import Flask, render_template, redirect, request, url_for, flash, jsonify, session, abort, send_file, make_response, g, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from sqlalchemy import text
from werkzeug.utils import secure_filename
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature
from PIL import Image, ImageOps
import qrcode
from io import BytesIO
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from sql_operations import direct_create_order, direct_get_order, direct_cart_operations, direct_get_products, direct_create_user, direct_get_user, direct_create_product
from create_order_direct import direct_create_order

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///pos.db')
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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='UGX')
    stock = db.Column(db.Float, nullable=False, default=0)
    max_stock = db.Column(db.Float, nullable=False, default=0)
    reorder_point = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(10), nullable=False, default='pcs')
    category = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    barcode = db.Column(db.String(50), unique=True, nullable=True, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stock_movements = db.relationship('StockMovement', backref='product', lazy=True)

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

    def update_stock(self, quantity, movement_type):
        if movement_type == 'sale':
            self.stock -= quantity
        elif movement_type == 'restock':
            self.stock += quantity
        
        movement = StockMovement(
            product_id=self.id,
            quantity=quantity,
            movement_type=movement_type,
            remaining_stock=self.stock
        )
        db.session.add(movement)

    def __repr__(self):
        return f'<Product {self.name}>'

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Quantity in kgs/ltrs
    movement_type = db.Column(db.String(20), nullable=False)  # 'sale' or 'restock'
    remaining_stock = db.Column(db.Float, nullable=False)  # Stock level after movement
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

class PriceChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='price_history')
    changed_by = db.relationship('User')

class Order(db.Model):
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Make nullable for anonymous users
    status = db.Column(db.String(20), default='active')
    items = db.relationship('CartItem', backref='cart', lazy=True)

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
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin'))
        elif current_user.is_staff:
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            
            if not next_page or url_parse(next_page).netloc != '':
                if user.is_admin:
                    next_page = url_for('admin')
                elif user.is_staff:
                    next_page = url_for('staff_dashboard')
                else:
                    next_page = url_for('index')
            
            return redirect(next_page)
        else:
            flash('Invalid username or password')
    
    return versioned_render_template('login.html')

@app.route('/logout')
@login_required
def logout():
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
                existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
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
    try:
        # Get sales data for the last 7 days
        dates = []
        sales_data = []
        for i in range(6, -1, -1):
            date = datetime.now().date() - timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))
            sales = Order.query.filter(
                db.func.date(Order.order_date) == date
            ).with_entities(db.func.sum(Order.total_amount)).scalar() or 0
            sales_data.append(float(sales))

        # Get today's total sales
        today = datetime.now().date()
        today_sales = Order.query.filter(
            db.func.date(Order.order_date) == today
        ).with_entities(db.func.sum(Order.total_amount)).scalar() or 0

        # Get product counts
        total_products = Product.query.count()
        low_stock_products = Product.query.filter(Product.stock < 10).count()
        out_of_stock_products = Product.query.filter(Product.stock == 0).count()
        
        # Get all products for product management
        products = Product.query.all()

        # Get recent stock movements
        recent_movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(10).all()

        # Get admin users
        admin_users = User.query.filter_by(is_admin=True).all()

        return render_template('admin.html', 
                             dates=dates, 
                             sales_data=sales_data,
                             today_sales=today_sales,
                             total_products=total_products,
                             low_stock_products=low_stock_products,
                             out_of_stock_products=out_of_stock_products,
                             recent_movements=recent_movements,
                             products=products,
                             admin_users=admin_users)
    except Exception as e:
        logger.error(f'Error in admin route: {str(e)}')
        flash('An error occurred while loading the admin dashboard', 'error')
        return redirect(url_for('index'))

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
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('manage_staff'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Staff user "{username}" has been deleted', 'success')
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
            existing_user = User.query.filter(User.email == email, User.id != user.id).first()
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
    if user.id == current_user.id:
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
            cart = Cart.query.filter_by(user_id=current_user.id, status='active').first()
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
                cart.user_id = current_user.id
            db.session.add(cart)
            db.session.commit()
            if not current_user.is_authenticated:
                session['cart_id'] = cart.id
        
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
        
        # Get cart items and calculate total
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        total_amount = sum(item.quantity * item.product.price for item in cart_items)
        
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
            cart = Cart.query.filter_by(user_id=current_user.id, status='active').first()
        else:
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = current_user.id
            
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

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    try:
        # Get the correct cart - same logic as in view_cart
        cart = None
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=current_user.id, status='active').first()
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
                'customer_address': request.form.get('customer_address', session.get('customer_address', ''))
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
            
            if error:
                # If it's a detected duplicate, we can still proceed to the receipt
                if "duplicate order" in error.lower() and order:
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
            order = get_order_by_id(order.id)
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
            flash('Order not found', 'error')
            return redirect(url_for('index'))
            
        # Add tax rate for receipt calculations
        tax_rate = 0.18  # 18% VAT
        # Pass current_user to template even for anonymous users
        return render_template('receipt.html', order=order, tax_rate=tax_rate, current_user=current_user)
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error loading receipt for order {order_id}: {str(e)}")
        flash(f"Error loading receipt: {str(e)}", 'error')
        return redirect(url_for('index'))
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
        if hasattr(order, 'customer_id') and order.customer_id != current_user.id and not current_user.is_admin:
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
            else:
                product.update_stock(quantity, 'restock')
                db.session.commit()
                flash(f'Successfully restocked {quantity} {product.unit} of {product.name}', 'success')
                return redirect(url_for('admin'))
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
            description = request.form.get('description', '')
            price = float(request.form.get('price', 0))
            stock = float(request.form.get('stock', 0))
            max_stock = float(request.form.get('max_stock', 0))
            reorder_point = float(request.form.get('reorder_point', 0))
            unit = request.form.get('unit', 'pcs')
            category = request.form.get('category', '')
            image_url = request.form.get('image_url', '')
            barcode = request.form.get('barcode', '')
            currency = request.form.get('currency', 'UGX')

            if not name:
                flash('Please provide a product name', 'error')
                return redirect(url_for('add_product'))
                
            if price <= 0:
                flash('Please provide a valid price greater than zero', 'error')
                return redirect(url_for('add_product'))

            # Check if barcode already exists (only if it's not empty)
            if barcode:
                existing_product = Product.query.filter_by(barcode=barcode).first()
                if existing_product:
                    flash('A product with this barcode already exists.', 'error')
                    return redirect(url_for('add_product'))
            
            # Create the product
            product = Product(
                name=name,
                description=description,
                price=price,
                currency=currency,
                stock=stock,
                max_stock=max_stock,
                reorder_point=reorder_point,
                unit=unit,
                category=category,
                image_url=image_url,
                barcode=barcode if barcode else None  # Store None if barcode is empty
            )

            db.session.add(product)
            db.session.commit()

            # Record stock movement if initial stock is provided
            if stock > 0:
                movement = StockMovement(
                    product_id=product.id,
                    quantity=stock,
                    movement_type='restock',
                    remaining_stock=stock,
                    notes=f'Initial stock for {name}'
                )
                db.session.add(movement)
                db.session.commit()

            flash(f'Product "{name}" added successfully!', 'success')
            return redirect(url_for('admin'))
        except ValueError as e:
            db.session.rollback()
            logger.error(f'ValueError in add_product: {str(e)}')
            flash('Please enter valid numbers for price and stock', 'error')
            return redirect(url_for('add_product'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error adding product: {str(e)}')
            flash(f'An error occurred while adding the product: {str(e)}', 'error')
            return redirect(url_for('add_product'))

    return render_template('add_product.html', 
                          units=get_product_units(), 
                          currencies=get_currencies(),
                          grocery_categories=get_grocery_categories(),
                          grocery_items=get_grocery_items())

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
            cart = Cart.query.filter_by(user_id=current_user.id, status='active').first()
        else:
            cart_id = session.get('cart_id')
            if cart_id:
                cart = Cart.query.get(cart_id)
                if cart and cart.status != 'active':
                    cart = None

        if not cart:
            cart = Cart(status='active')
            if current_user.is_authenticated:
                cart.user_id = current_user.id
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
        # Get date range parameters, default to last 30 days
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError as e:
                logger.error(f'Invalid date format: {str(e)}')
                return jsonify({'error': f'Invalid date format. Use YYYY-MM-DD format. Details: {str(e)}'}), 400
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=29)  # Last 30 days
        
        # Ensure date range is valid
        if start_date > end_date:
            return jsonify({'error': 'Start date must be before end date'}), 400
            
        # Limit to reasonable date range (maximum 1 year)
        if (end_date - start_date).days > 365:
            return jsonify({'error': 'Date range too large. Maximum range is 1 year'}), 400
            
        # Generate list of dates
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Get sales data
        sales_data = []
        profit_data = []
        
        for date in dates:
            # Get total sales for the day using more efficient query
            daily_sales = db.session.query(db.func.sum(Order.total_amount)).filter(
                db.func.date(Order.order_date) == date
            ).scalar()
            
            daily_total = float(daily_sales) if daily_sales else 0.0
            sales_data.append(daily_total)
            
            # Calculate profit (simplified as 20% of sales)
            # In a real system, you would use actual cost data for each product
            daily_profit = daily_total * 0.2
            profit_data.append(daily_profit)
        
        dates_str = [date.strftime('%Y-%m-%d') for date in dates]
        
        return jsonify({
            'dates': dates_str,
            'sales': sales_data,
            'profit': profit_data
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
        
        # Process each month
        for i in range(months-1, -1, -1):
            try:
                # Calculate month dates
                current_month = add_months(end_date, -i)
                next_month = add_months(current_month, 1)
                
                # Get orders for the month using more efficient query
                monthly_total = db.session.query(db.func.sum(Order.total_amount)).filter(
                    db.func.date(Order.order_date) >= current_month,
                    db.func.date(Order.order_date) < next_month
                ).scalar()
                
                monthly_total = float(monthly_total) if monthly_total else 0.0
                sales_data.append(monthly_total)
                
                # Calculate profit (simplified as 20% of sales)
                monthly_profit = monthly_total * 0.2
                profit_data.append(monthly_profit)
                
                # Format month label
                month_label = current_month.strftime('%B %Y')
                months_data.append(month_label)
            except Exception as month_err:
                logger.error(f'Error processing month {i}: {str(month_err)}')
                # Add zero values for months with errors to maintain data array length
                sales_data.append(0.0)
                profit_data.append(0.0)
                months_data.append(f"Error: Month -{i}")
        
        return jsonify({
            'months': months_data,
            'sales': sales_data,
            'profit': profit_data
        })
    
    except Exception as e:
        # Log detailed error information
        import traceback
        logger.error(f'Error in monthly sales API: {str(e)}')
        logger.error(traceback.format_exc())
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
        
        # Process each year
        for year in range(current_year - years_count + 1, current_year + 1):
            # Calculate year dates
            year_start = datetime(year, 1, 1).date()
            year_end = datetime(year, 12, 31).date()
            
            # Get orders for the year using more efficient query
            yearly_total = db.session.query(db.func.sum(Order.total_amount)).filter(
                db.func.date(Order.order_date) >= year_start,
                db.func.date(Order.order_date) <= year_end
            ).scalar()
            
            yearly_total = float(yearly_total) if yearly_total else 0.0
            sales_data.append(yearly_total)
            
            # Calculate profit (simplified as 20% of sales)
            yearly_profit = yearly_total * 0.2
            profit_data.append(yearly_profit)
            
            # Add year label
            years_data.append(str(year))
        
        return jsonify({
            'years': years_data,
            'sales': sales_data,
            'profit': profit_data
        })
    
    except Exception as e:
        # Log detailed error information
        import traceback
        logger.error(f'Error in yearly sales API: {str(e)}')
        logger.error(traceback.format_exc())
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
            changed_by_id=current_user.id
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
            product.max_stock = float(request.form.get('max_stock', 0))
            product.reorder_point = float(request.form.get('reorder_point', 0))
            product.unit = request.form.get('unit', 'pcs')
            product.category = request.form.get('category')
            product.image_url = request.form.get('image_url')
            product.barcode = request.form.get('barcode')
            product.currency = request.form.get('currency', 'UGX')
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin'))
        except ValueError:
            flash('Please enter valid numbers for price and stock levels', 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating product: {str(e)}')
            flash('An error occurred while updating the product', 'error')
    
    return render_template('edit_product.html', 
                          product=product, 
                          units=get_product_units(),
                          currencies=get_currencies(),
                          grocery_categories=get_grocery_categories(),
                          grocery_items=get_grocery_items())

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
    """Create a sale for in-store customers (staff/admin only)"""
    # Get all available products
    products = Product.query.filter(Product.stock > 0).all()
    
    if request.method == 'POST':
        try:
            # Get customer information
            customer_data = {
                'customer_name': request.form.get('customer_name', ''),
                'customer_email': request.form.get('customer_email', ''),
                'customer_phone': request.form.get('customer_phone', ''),
                'customer_address': request.form.get('customer_address', '')
            }
            
            # Prepare items data
            items_data = []
            
            for product in products:
                quantity_str = request.form.get(f'quantity-{product.id}', '0')
                if not quantity_str or not quantity_str.strip():
                    continue
                
                try:
                    quantity = int(quantity_str)
                except ValueError:
                    continue
                    
                if quantity <= 0:
                    continue
                
                # Re-query to get fresh stock value
                fresh_product = Product.query.get(product.id)
                if not fresh_product:
                    continue
                    
                if quantity > fresh_product.stock:
                    flash(f'Not enough stock for {fresh_product.name}. Only {fresh_product.stock} available.', 'error')
                    continue
                
                # Add item to the list
                items_data.append({
                    'product_id': fresh_product.id,
                    'quantity': quantity,
                    'price': fresh_product.price,
                    'name': fresh_product.name
                })
            
            # Fail if no valid items
            if not items_data:
                flash('No valid items selected for purchase.', 'error')
                return redirect(url_for('in_store_sale'))
            
            # Use the centralized function to create the order
            order, error = create_order(customer_data, items_data, 'in-store')
            
            if error:
                # If it's a detected duplicate, we can still proceed to the receipt
                if "duplicate order" in error.lower() and order:
                    flash('It appears this order was already processed!', 'info')
                    return redirect(url_for('print_receipt', order_id=order.id))
                else:
                    flash(error, 'error')
                    return redirect(url_for('in_store_sale'))
            
            # Redirect to receipt
            flash('Order created successfully!', 'success')
            return redirect(url_for('print_receipt', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating in-store sale: {str(e)}')
            flash(f'Error creating order: {str(e)}', 'error')
    
    # GET request - show the form
    return render_template('in_store_sale.html', products=products)

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
        order = Order.query.get_or_404(order_id)
        order.status = 'completed'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} marked as processed.'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error marking order as processed: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/service-worker.js')
def service_worker():
    """
    Serve the service worker script without requiring authentication
    This must be accessible to allow offline functionality
    """
    logger.info("Service worker requested")
    
    # Default service worker if file not found
    default_worker = """
    // Default service worker
    self.addEventListener('fetch', function(event) {
      event.respondWith(
        fetch(event.request).catch(function() {
          return caches.match(event.request);
        })
      );
    });
    """
    
    try:
        worker_path = os.path.join(app.static_folder, 'service-worker.js')
        
        # Check if file exists
        if os.path.exists(worker_path) and os.path.isfile(worker_path):
            with open(worker_path, 'r') as file:
                content = file.read()
        else:
            logger.warning("service-worker.js not found, using default")
            content = default_worker
        
        response = make_response(content)
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    except Exception as e:
        logger.error(f"Error serving service-worker.js: {e}")
        response = make_response(default_worker)
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Cache-Control'] = 'no-cache'
        return response

@app.route('/offline.html')
def offline():
    return render_template('offline.html')

@app.route('/api/sync_offline_order', methods=['POST'])
@login_required
def sync_offline_order():
    try:
        # Get order data from request
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Extract order details
        customer_data = {
            'customer_name': data.get('customer_name', ''),
            'customer_email': data.get('customer_email', ''),
            'customer_phone': data.get('customer_phone', ''),
            'customer_address': data.get('customer_address', '')
        }
        
        raw_items = data.get('items', [])
        offline_timestamp = data.get('offlineTimestamp')
        
        # Validate basic data
        if not raw_items or not isinstance(raw_items, list):
            return jsonify({'success': False, 'error': 'Invalid items data'}), 400
            
        # Prepare items data
        items_data = []
        
        # Check stock and prepare items
        for item in raw_items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            
            if not product_id or quantity <= 0:
                continue
                
            product = Product.query.get(product_id)
            if not product:
                continue
                
            # Skip if not enough stock (client might have stale data)
            if quantity > product.stock:
                return jsonify({
                    'success': False, 
                    'error': f'Not enough stock for {product.name}. Only {product.stock} available.'
                }), 400
                
            items_data.append({
                'product_id': product_id,
                'quantity': quantity,
                'price': product.price,
                'name': product.name
            })
            
        # If no valid items, return error
        if not items_data:
            return jsonify({'success': False, 'error': 'No valid items in order'}), 400
            
        # Create the order using the centralized function
        order, error = create_order(customer_data, items_data, 'offline-sync')
        
        if error:
            # If it's a detected duplicate, we can still consider it a success
            if "duplicate order" in error.lower() and order:
                return jsonify({
                    'success': True,
                    'message': f'Order #{order.id} was already synced',
                    'order_id': order.id,
                    'duplicate': True
                })
            else:
                return jsonify({'success': False, 'error': error}), 500
        
        return jsonify({
            'success': True,
            'message': f'Order #{order.id} successfully synced',
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error syncing offline order: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/my_sales')
@login_required
@staff_required
def my_sales():
    """Display all sales created by the current staff member"""
    try:
        # Get URL parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of orders per page
        
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Count total orders for pagination
        cursor.execute("""
            SELECT COUNT(*)
            FROM "order"
            WHERE created_by_id = ?
            ORDER BY order_date DESC
        """, (current_user.id,))
        
        total_orders = cursor.fetchone()[0]
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get paginated orders
        cursor.execute("""
            SELECT id, customer_name, order_date, total_amount, status, viewed
            FROM "order"
            WHERE created_by_id = ?
            ORDER BY order_date DESC
            LIMIT ? OFFSET ?
        """, (current_user.id, per_page, offset))
        
        order_data = cursor.fetchall()
        
        # Create a list of SimpleNamespace objects to mimic ORM
        orders = []
        for order_row in order_data:
            order = SimpleNamespace(
                id=order_row[0],
                customer_name=order_row[1],
                order_date=order_row[2],
                total_amount=order_row[3],
                status=order_row[4],
                viewed=order_row[5]
            )
            orders.append(order)
        
        # Calculate total pages for pagination
        total_pages = (total_orders + per_page - 1) // per_page
        
        conn.close()
        
        return render_template('staff/orders.html', 
                              orders=orders, 
                              page=page, 
                              total_pages=total_pages)
    except Exception as e:
        flash('Error loading orders: ' + str(e), 'danger')
        app.logger.error(f"Error in my_sales: {str(e)}")
        return redirect(url_for('staff_dashboard'))

# Method to identify if user agent is from a mobile or desktop device
def is_mobile():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_agents = ['android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(agent in user_agent for agent in mobile_agents)

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Admin user created successfully!')
        else:
            print('Admin user already exists.')

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
        ]),
        
        # International Foods
        ('international', 'International Foods', [
            ('asian', 'Asian Foods'),
            ('mexican', 'Mexican Foods'),
            ('italian', 'Italian Foods'),
            ('indian', 'Indian Foods'),
            ('middle_eastern', 'Middle Eastern Foods'),
            ('african', 'African Foods'),
            ('european', 'European Foods')
        ]),
        
        # Breakfast Foods
        ('breakfast', 'Breakfast Foods', [
            ('cereal', 'Cereal'),
            ('oatmeal', 'Oatmeal & Hot Cereals'),
            ('breakfast_bars', 'Breakfast & Granola Bars'),
            ('pancake_waffle', 'Pancake & Waffle Mixes'),
            ('syrup', 'Syrups & Toppings'),
            ('jams_spreads', 'Jams, Jellies & Spreads')
        ]),
        
        # Canned & Jarred Goods
        ('canned_jarred', 'Canned & Jarred Goods', [
            ('canned_vegetables', 'Canned Vegetables'),
            ('canned_fruits', 'Canned Fruits'),
            ('canned_meat', 'Canned Meat & Seafood'),
            ('canned_soups', 'Canned Soups'),
            ('canned_beans', 'Canned Beans'),
            ('pickles_olives', 'Pickles & Olives'),
            ('sauces_pastes', 'Sauces & Pastes')
        ]),
        
        # Baby Products
        ('baby', 'Baby Products', [
            ('baby_food', 'Baby Food'),
            ('formula', 'Baby Formula'),
            ('diapers', 'Diapers & Wipes'),
            ('baby_care', 'Baby Care Products')
        ]),
        
        # Health & Wellness
        ('health', 'Health & Wellness', [
            ('vitamins', 'Vitamins & Supplements'),
            ('pain_relief', 'Pain Relief'),
            ('first_aid', 'First Aid'),
            ('cold_flu', 'Cold & Flu Medications'),
            ('digestive_health', 'Digestive Health'),
            ('personal_care', 'Personal Care')
        ]),
        
        # Household
        ('household', 'Household', [
            ('cleaning', 'Cleaning Supplies'),
            ('laundry', 'Laundry Products'),
            ('paper_products', 'Paper Products'),
            ('food_storage', 'Food Storage'),
            ('disposable_tableware', 'Disposable Tableware'),
            ('pet_supplies', 'Pet Supplies')
        ]),
        
        # Alcoholic Beverages
        ('alcohol', 'Alcoholic Beverages', [
            ('beer', 'Beer'),
            ('wine', 'Wine'),
            ('spirits', 'Spirits & Liquor'),
            ('mixers', 'Mixers & Cocktail Ingredients'),
            ('hard_seltzers', 'Hard Seltzers & Ciders')
        ]),
        
        # Organic & Natural
        ('organic', 'Organic & Natural', [
            ('organic_produce', 'Organic Produce'),
            ('organic_dairy', 'Organic Dairy'),
            ('organic_meat', 'Organic Meat'),
            ('organic_pantry', 'Organic Pantry Items'),
            ('natural_foods', 'Natural Foods')
        ]),
        
        # Seasonal Products
        ('seasonal', 'Seasonal Products', [
            ('holiday', 'Holiday Items'),
            ('seasonal_produce', 'Seasonal Produce'),
            ('grilling', 'Grilling & Outdoor'),
            ('school_supplies', 'Back to School'),
            ('seasonal_decor', 'Seasonal Décor')
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
            {'name': 'Grapes', 'description': 'Sweet seedless grapes', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Strawberries', 'description': 'Fresh ripe strawberries', 'unit': 'box', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Blueberries', 'description': 'Organic blueberries', 'unit': 'box', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Watermelon', 'description': 'Large sweet watermelon', 'unit': 'pcs', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Pineapple', 'description': 'Ripe golden pineapple', 'unit': 'pcs', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Mango', 'description': 'Sweet tropical mango', 'unit': 'pcs', 'category_group': 'produce', 'category': 'fresh_fruits'},
            {'name': 'Avocados', 'description': 'Ripe Hass avocados', 'unit': 'pcs', 'category_group': 'produce', 'category': 'fresh_fruits'}
        ],
        
        # Fresh Vegetables
        'fresh_vegetables': [
            {'name': 'Lettuce', 'description': 'Fresh green lettuce', 'unit': 'head', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Spinach', 'description': 'Organic baby spinach', 'unit': 'bag', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Broccoli', 'description': 'Fresh broccoli florets', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Carrots', 'description': 'Fresh orange carrots', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Tomatoes', 'description': 'Ripe red tomatoes', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Bell Peppers', 'description': 'Colorful bell peppers', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Onions', 'description': 'Fresh yellow onions', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Potatoes', 'description': 'Russet potatoes', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Garlic', 'description': 'Fresh garlic bulbs', 'unit': 'pcs', 'category_group': 'produce', 'category': 'fresh_vegetables'},
            {'name': 'Mushrooms', 'description': 'Fresh white mushrooms', 'unit': 'kg', 'category_group': 'produce', 'category': 'fresh_vegetables'}
        ],
        
        # Fresh Herbs
        'herbs': [
            {'name': 'Basil', 'description': 'Fresh sweet basil', 'unit': 'bunch', 'category_group': 'produce', 'category': 'herbs'},
            {'name': 'Parsley', 'description': 'Fresh Italian parsley', 'unit': 'bunch', 'category_group': 'produce', 'category': 'herbs'},
            {'name': 'Cilantro', 'description': 'Fresh cilantro/coriander', 'unit': 'bunch', 'category_group': 'produce', 'category': 'herbs'},
            {'name': 'Mint', 'description': 'Fresh mint leaves', 'unit': 'bunch', 'category_group': 'produce', 'category': 'herbs'},
            {'name': 'Rosemary', 'description': 'Fresh rosemary sprigs', 'unit': 'bunch', 'category_group': 'produce', 'category': 'herbs'}
        ],
        
        # Meat & Poultry
        'meat_poultry': [
            {'name': 'Ground Beef', 'description': 'Lean ground beef', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'beef'},
            {'name': 'Beef Steak', 'description': 'Premium beef steak', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'beef'},
            {'name': 'Chicken Breast', 'description': 'Boneless chicken breast', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'poultry'},
            {'name': 'Chicken Thighs', 'description': 'Boneless chicken thighs', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'poultry'},
            {'name': 'Pork Chops', 'description': 'Center-cut pork chops', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'pork'},
            {'name': 'Bacon', 'description': 'Smoked bacon strips', 'unit': 'pack', 'category_group': 'meat_seafood', 'category': 'pork'}
        ],
        
        # Seafood
        'seafood': [
            {'name': 'Salmon', 'description': 'Fresh Atlantic salmon', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'fish'},
            {'name': 'Tuna', 'description': 'Fresh tuna steaks', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'fish'},
            {'name': 'Shrimp', 'description': 'Large peeled shrimp', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'shellfish'},
            {'name': 'Tilapia', 'description': 'Fresh tilapia fillets', 'unit': 'kg', 'category_group': 'meat_seafood', 'category': 'fish'}
        ],
        
        # Dairy & Eggs
        'dairy_eggs': [
            {'name': 'Milk', 'description': 'Fresh whole milk', 'unit': 'l', 'category_group': 'dairy_eggs', 'category': 'milk'},
            {'name': 'Eggs', 'description': 'Large fresh eggs', 'unit': 'dozen', 'category_group': 'dairy_eggs', 'category': 'eggs'},
            {'name': 'Butter', 'description': 'Unsalted butter', 'unit': 'pcs', 'category_group': 'dairy_eggs', 'category': 'butter'},
            {'name': 'Cheddar', 'description': 'Sharp cheddar cheese', 'unit': 'kg', 'category_group': 'dairy_eggs', 'category': 'cheese'},
            {'name': 'Yogurt', 'description': 'Plain Greek yogurt', 'unit': 'pcs', 'category_group': 'dairy_eggs', 'category': 'yogurt'}
        ],
        
        # Bakery
        'bakery': [
            {'name': 'White Bread', 'description': 'Sliced white bread', 'unit': 'loaf', 'category_group': 'bakery', 'category': 'bread'},
            {'name': 'Wheat Bread', 'description': 'Whole wheat bread', 'unit': 'loaf', 'category_group': 'bakery', 'category': 'bread'},
            {'name': 'Bagels', 'description': 'Fresh plain bagels', 'unit': 'pack', 'category_group': 'bakery', 'category': 'rolls_buns'},
            {'name': 'Muffins', 'description': 'Blueberry muffins', 'unit': 'pack', 'category_group': 'bakery', 'category': 'cookies'}
        ],
        
        # Pantry Staples
        'pantry': [
            {'name': 'Rice', 'description': 'Long grain white rice', 'unit': 'kg', 'category_group': 'pantry', 'category': 'rice_grains'},
            {'name': 'Pasta', 'description': 'Spaghetti pasta', 'unit': 'pack', 'category_group': 'pantry', 'category': 'pasta'},
            {'name': 'Flour', 'description': 'All-purpose flour', 'unit': 'kg', 'category_group': 'pantry', 'category': 'baking'},
            {'name': 'Sugar', 'description': 'Granulated white sugar', 'unit': 'kg', 'category_group': 'pantry', 'category': 'baking'},
            {'name': 'Olive Oil', 'description': 'Extra virgin olive oil', 'unit': 'bottle', 'category_group': 'pantry', 'category': 'oils_vinegars'}
        ],
        
        # Beverages
        'beverages': [
            {'name': 'Water', 'description': 'Bottled mineral water', 'unit': 'bottle', 'category_group': 'beverages', 'category': 'water'},
            {'name': 'Orange Juice', 'description': 'Fresh squeezed orange juice', 'unit': 'l', 'category_group': 'beverages', 'category': 'juice'},
            {'name': 'Coffee', 'description': 'Ground coffee beans', 'unit': 'bag', 'category_group': 'beverages', 'category': 'coffee'},
            {'name': 'Tea', 'description': 'Black tea bags', 'unit': 'box', 'category_group': 'beverages', 'category': 'tea'},
            {'name': 'Soda', 'description': 'Carbonated soft drink', 'unit': 'bottle', 'category_group': 'beverages', 'category': 'soda'}
        ]
    }

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
        logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'success': False, 'error': str(e), 'count': 0})

@app.route('/staff_dashboard')
@login_required
@staff_required
def staff_dashboard():
    try:
        # Get recent orders (both online and in-store)
        try:
            recent_orders = Order.query.order_by(Order.order_date.desc()).limit(20).all()
        except Exception as e:
            app.logger.error(f"Error fetching recent orders: {str(e)}")
            # Fallback to direct SQL
            recent_orders = []
            try:
                result = db.session.execute(
                    text("SELECT id, customer_name, total_amount, order_date, status FROM 'order' ORDER BY order_date DESC LIMIT 20")
                )
                for row in result:
                    # Create a simplified order object with just the fields we need
                    # Convert string date to datetime if needed
                    order_date = row[3]
                    if isinstance(order_date, str):
                        try:
                            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            # If conversion fails, use current time as fallback
                            order_date = datetime.utcnow()
                            
                    order = SimpleNamespace(
                        id=row[0],
                        customer_name=row[1],
                        total_amount=row[2],
                        order_date=order_date,
                        status=row[4]
                    )
                    recent_orders.append(order)
            except Exception as sql_e:
                app.logger.error(f"Fallback SQL also failed: {str(sql_e)}")
        
        # Get pending orders that need to be processed
        try:
            pending_orders = Order.query.filter_by(status='pending').all()
        except Exception as e:
            app.logger.error(f"Error fetching pending orders: {str(e)}")
            pending_orders = []
            try:
                result = db.session.execute(
                    text("SELECT id, customer_name, total_amount, order_date FROM 'order' WHERE status = 'pending'")
                )
                for row in result:
                    # Convert string date to datetime if needed
                    order_date = row[3]
                    if isinstance(order_date, str):
                        try:
                            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            # If conversion fails, use current time as fallback
                            order_date = datetime.utcnow()
                            
                    order = SimpleNamespace(
                        id=row[0],
                        customer_name=row[1],
                        total_amount=row[2],
                        order_date=order_date,
                        status='pending'
                    )
                    pending_orders.append(order)
            except Exception as sql_e:
                app.logger.error(f"Fallback SQL also failed: {str(sql_e)}")
        
        # Count of orders by status
        order_counts = {}
        try:
            order_counts = {
                'pending': Order.query.filter_by(status='pending').count(),
                'processing': Order.query.filter_by(status='processing').count(),
                'completed': Order.query.filter_by(status='completed').count()
            }
        except Exception as e:
            app.logger.error(f"Error fetching order counts: {str(e)}")
            try:
                # Fallback to direct SQL counts
                pending = db.session.execute(text("SELECT COUNT(*) FROM 'order' WHERE status = 'pending'")).scalar() or 0
                processing = db.session.execute(text("SELECT COUNT(*) FROM 'order' WHERE status = 'processing'")).scalar() or 0
                completed = db.session.execute(text("SELECT COUNT(*) FROM 'order' WHERE status = 'completed'")).scalar() or 0
                
                order_counts = {
                    'pending': pending,
                    'processing': processing,
                    'completed': completed
                }
            except Exception as sql_e:
                app.logger.error(f"Fallback SQL counts also failed: {str(sql_e)}")
                order_counts = {'pending': 0, 'processing': 0, 'completed': 0}
        
        return render_template('staff/dashboard.html', 
                              recent_orders=recent_orders,
                              pending_orders=pending_orders,
                              order_counts=order_counts)
    except Exception as e:
        app.logger.error(f"Critical error in staff_dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template('staff/dashboard.html', 
                              recent_orders=[],
                              pending_orders=[],
                              order_counts={'pending': 0, 'processing': 0, 'completed': 0},
                              error=str(e))

@app.route('/staff/all-orders')
@login_required
@staff_required
def all_staff_orders():
    try:
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of orders per page
        
        # Get filter parameters
        status = request.args.get('status', '')
        order_type = request.args.get('order_type', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause for filters
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if order_type:
            where_clauses.append("order_type = ?")
            params.append(order_type)
        
        if start_date:
            try:
                # Parse the date string into a datetime object
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                where_clauses.append("date(order_date) >= date(?)")
                params.append(start_date_obj.strftime('%Y-%m-%d'))
            except ValueError:
                flash('Invalid start date format. Please use YYYY-MM-DD.', 'warning')
        
        if end_date:
            try:
                # Parse the date string into a datetime object
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                where_clauses.append("date(order_date) <= date(?)")
                params.append(end_date_obj.strftime('%Y-%m-%d'))
            except ValueError:
                flash('Invalid end date format. Please use YYYY-MM-DD.', 'warning')
        
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
        
        return render_template('staff/all_orders.html', 
                             orders=orders, 
                             page=page, 
                             total_pages=total_pages,
                             status=status,
                             order_type=order_type,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        flash('Error loading orders: ' + str(e), 'danger')
        app.logger.error(f"Error in all_staff_orders: {str(e)}")
        return redirect(url_for('staff_dashboard'))

@app.route('/staff/order/<int:order_id>')
@login_required
@staff_required
def staff_order_detail(order_id):
    try:
        # Use direct SQL instead of ORM to avoid column issues
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Check if payment_method and payment_status columns exist
        cursor.execute("PRAGMA table_info('order')")
        columns = [col[1] for col in cursor.fetchall()]
        has_payment_columns = 'payment_method' in columns and 'payment_status' in columns
        has_payment_id = 'payment_id' in columns
        
        # Get the order details
        if has_payment_columns and has_payment_id:
            query = """
                SELECT id, customer_id, order_date, total_amount, status, 
                       customer_name, customer_phone, customer_email, customer_address,
                       order_type, created_by_id, updated_at, completed_at, viewed, viewed_at,
                       payment_method, payment_status, payment_id
                FROM "order"
                WHERE id = ?
            """
        else:
            query = """
                SELECT id, customer_id, order_date, total_amount, status, 
                       customer_name, customer_phone, customer_email, customer_address,
                       order_type, created_by_id, updated_at, completed_at, viewed, viewed_at
                FROM "order"
                WHERE id = ?
            """
        
        cursor.execute(query, (order_id,))
        order_data = cursor.fetchone()
        
        if not order_data:
            flash('Order not found', 'error')
            return redirect(url_for('staff_dashboard'))
        
        # Get staff name who created the order
        staff_name = None
        if order_data[10]:  # created_by_id
            cursor.execute("SELECT username FROM user WHERE id = ?", (order_data[10],))
            staff_result = cursor.fetchone()
            if staff_result:
                staff_name = staff_result[0]
        
        # Get order items
        cursor.execute("""
            SELECT oi.id, oi.product_id, oi.quantity, oi.price, p.name as product_name, p.category
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
            'created_by': SimpleNamespace(username=staff_name) if staff_name else None,
            'updated_at': order_data[11],
            'completed_at': order_data[12],
            'viewed': order_data[13],
            'viewed_at': order_data[14],
        }
        
        # Add payment fields if they exist
        if has_payment_columns and has_payment_id and len(order_data) >= 18:
            order_dict['payment_method'] = order_data[15]
            order_dict['payment_status'] = order_data[16]
            order_dict['payment_id'] = order_data[17]
        else:
            # Provide default values
            order_dict['payment_method'] = 'Cash'
            order_dict['payment_status'] = 'paid' if order_data[4] == 'completed' else 'pending'
            order_dict['payment_id'] = None
        
        order = SimpleNamespace(**order_dict)
        
        # Create SimpleNamespace objects for order items and attach to order
        items = []
        for item_data in order_items:
            item = SimpleNamespace(
                id=item_data[0],
                product_id=item_data[1],
                quantity=item_data[2],
                price=item_data[3],
                subtotal=item_data[2] * item_data[3],
                product=SimpleNamespace(
                    name=item_data[4],
                    category=item_data[5]
                )
            )
            items.append(item)
        
        # Add items as a property to the order
        order.items = items
        
        conn.close()
        
        # Pass tax rate for calculations
        tax_rate = 0.18  # 18% VAT
        
        return render_template('staff/order_detail.html', order=order, tax_rate=tax_rate)
    except Exception as e:
        app.logger.error(f"Error in staff_order_detail: {str(e)}")
        flash(f"Error viewing order: {str(e)}", "error")
        return redirect(url_for('staff_dashboard'))

def create_order(customer_data, items_data, order_type):
    """
    Centralized function to create orders from different contexts, with fallback to direct SQL
    """
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
                    product.update_stock(item_data['quantity'], 'sale')
            
            # Generate reference number
            now = datetime.utcnow()
            order.reference_number = f"ORD-{now.strftime('%Y%m%d')}-{order.id}"
            
            # Commit the transaction
            db.session.commit()
            
            # Return the created order
            return order, None
            
        except SQLAlchemyError as e:
            # If we get a SQLAlchemy error, try the direct SQL approach
            logger.warning(f"SQLAlchemy error when creating order, falling back to direct SQL: {str(e)}")
            db.session.rollback()
            
            # Fall back to direct SQL approach
            order_id, reference = direct_create_order(customer_data, items_data, order_type)
            
            if order_id:
                # Get the order using our resilient function
                order = get_order_by_id(order_id)
                if order:
                    return order, None
                else:
                    # If we can't get the order, return a generic success message
                    logger.warning(f"Created order {order_id} with direct SQL but can't access it")
                    return None, f"Order created with ID {order_id}, but couldn't be retrieved"
            else:
                return None, reference  # reference contains the error message
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating order: {str(e)}")
        return None, f"Error creating order: {str(e)}"



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
    """Endpoint for troubleshooting - returns system diagnostics"""
    diagnostics = {
        'timestamp': datetime.utcnow().isoformat(),
        'app_version': APP_VERSION,
        'static_folder': app.static_folder,
        'static_url_path': app.static_url_path,
        'static_folder_exists': os.path.exists(app.static_folder),
        'static_folder_contents': os.listdir(app.static_folder) if os.path.exists(app.static_folder) else [],
        'service_worker_path': os.path.join(app.static_folder, 'service-worker.js'),
        'service_worker_exists': os.path.exists(os.path.join(app.static_folder, 'service-worker.js')),
        'current_path': request.path,
        'headers': dict(request.headers),
        'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'user_agent': request.user_agent.string if request.user_agent else None,
        'request_method': request.method,
    }
    
    return jsonify(diagnostics)

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for any unhandled URLs"""
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

@app.route('/api/check_new_orders', methods=['GET'])
def check_new_orders():
    try:
        # Check if user is staff (authenticated and has staff role)
        if not current_user.is_authenticated or not (current_user.is_staff or current_user.is_admin):
            # Return empty result for non-staff users instead of error
            return jsonify({'new_orders': 0, 'new_order': False, 'authenticated': False})
        
        # Use direct SQL query instead of ORM to avoid column issues
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Count unviewed orders
        cursor.execute("SELECT COUNT(*) FROM 'order' WHERE viewed = 0")
        new_orders = cursor.fetchone()[0]
        
        # If there are new orders, get the most recent one's details for the notification
        if new_orders > 0:
            cursor.execute("""
                SELECT id, customer_name, total_amount, order_date 
                FROM 'order' 
                WHERE viewed = 0 
                ORDER BY order_date DESC 
                LIMIT 1
            """)
            
            newest_order = cursor.fetchone()
            if newest_order:
                return jsonify({
                    'new_orders': new_orders,
                    'new_order': True,
                    'order_id': newest_order[0],
                    'customer_name': newest_order[1] if newest_order[1] else 'Customer',
                    'total_amount': f"{newest_order[2]:.2f}",
                    'currency': 'UGX',
                    'order_date': newest_order[3],
                    'authenticated': True
                })
        
        conn.close()
        return jsonify({'new_orders': new_orders, 'new_order': False, 'authenticated': True})
    except Exception as e:
        # Log the error and return a safe response
        app.logger.error(f"Error checking new orders: {str(e)}")
        return jsonify({'new_orders': 0, 'new_order': False, 'error': str(e), 'authenticated': False})

@app.route('/staff/orders')
@login_required
@staff_required
def staff_orders():
    try:
        # Get URL parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of orders per page
        
        # Get filter parameters
        status = request.args.get('status', '')
        order_type = request.args.get('order_type', '')
        
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause for filters
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if order_type:
            where_clauses.append("order_type = ?")
            params.append(order_type)
        
        # Construct the WHERE clause
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Limit to recent orders (last 30 days)
        if where_clauses:
            where_sql += " AND date(order_date) >= date('now', '-30 day')"
        else:
            where_sql = " WHERE date(order_date) >= date('now', '-30 day')"
        
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
        
        return render_template('staff/orders.html', 
                              orders=orders, 
                              page=page, 
                              total_pages=total_pages,
                              status=status,
                              order_type=order_type)
    except Exception as e:
        flash('Error loading recent orders: ' + str(e), 'danger')
        app.logger.error(f"Error in staff_orders: {str(e)}")
        return redirect(url_for('staff_dashboard'))

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
            # Direct database query with LEFT JOIN to handle missing products
            conn = sqlite3.connect('instance/pos.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get the order
            cursor.execute("""
            SELECT * FROM "order" WHERE id = ?
            """, (order_id,))
            
            order_row = cursor.fetchone()
            if not order_row:
                conn.close()
                logger.error(f"Order {order_id} not found in direct SQL")
                return None
                
            order_dict = dict(order_row)
            
            # Get the order items with LEFT JOIN to products
            cursor.execute("""
            SELECT oi.*, p.name as product_name, p.price as product_price 
            FROM order_item oi
            LEFT JOIN product p ON oi.product_id = p.id
            WHERE oi.order_id = ?
            """, (order_id,))
            
            items = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            # Create a SimpleOrder object to mimic the SQLAlchemy Order
            class SimpleOrder:
                def __init__(self, order_data, item_data):
                    # Basic order properties
                    self.id = order_data.get('id')
                    self.reference_number = order_data.get('reference_number', '')
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
                    
                    # Store item data for items property
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
            logger.error(f"Error in direct SQL retrieval: {str(inner_e)}")
            return None
    
    except Exception as e:
        logger.error(f"Error in get_order_by_id: {str(e)}")
        return None

if __name__ == '__main__':
    # Initialize database and create all tables
    init_db()
    # Run app with permissive host to allow access from all IPs in local network
    # This can help with network-related 403 errors
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True) 