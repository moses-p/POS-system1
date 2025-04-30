import logging
from sqlalchemy import inspect, MetaData, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("sqlalchemy_refresh.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def refresh_sqlalchemy_metadata():
    """
    Refresh SQLAlchemy metadata to reflect current database schema
    """
    try:
        # Use the same database URI as in the app
        db_path = os.path.join(os.getcwd(), 'instance', 'pos.db')
        db_uri = f'sqlite:///{db_path}'
        
        # Create engine and bind metadata
        engine = create_engine(db_uri)
        metadata = MetaData()
        metadata.bind = engine
        
        # Reflect all tables from the database
        metadata.reflect(bind=engine)
        
        # Check if order table is properly reflected
        inspector = inspect(engine)
        
        # Log all tables in the database
        tables = inspector.get_table_names()
        logger.info(f"Tables in database: {tables}")
        
        # Check if the order table exists
        if 'order' not in tables:
            logger.error("Order table not found in database")
            return False
            
        # Check columns in the order table
        columns = inspector.get_columns('order')
        column_names = [col['name'] for col in columns]
        logger.info(f"Columns in order table: {column_names}")
        
        # Check if reference_number column exists
        if 'reference_number' not in column_names:
            logger.error("reference_number column not found in order table")
            return False
            
        logger.info("SQLAlchemy metadata refreshed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error refreshing SQLAlchemy metadata: {str(e)}")
        return False

def create_model_patch():
    """
    Create a patch file with the updated Order model definition
    """
    try:
        patch_content = """
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
"""
        
        # Write the patch to a file
        with open('order_model_patch.py', 'w') as f:
            f.write(patch_content)
            
        logger.info("Created Order model patch file: order_model_patch.py")
        return True
    
    except Exception as e:
        logger.error(f"Error creating model patch: {str(e)}")
        return False

if __name__ == "__main__":
    # First rebuild the order table completely
    logger.info("Please run rebuild_order_table.py first to rebuild the order table")
    
    # Then refresh SQLAlchemy metadata
    if refresh_sqlalchemy_metadata():
        logger.info("SQLAlchemy metadata refreshed successfully")
        create_model_patch()
        
        logger.info("""
        Fix completed. Now do the following:
        
        1. Restart your Flask application to reload the SQLAlchemy models
        2. If issues persist, review the Order model in app.py and ensure it matches 
           the schema in the database
        """)
    else:
        logger.error("Failed to refresh SQLAlchemy metadata. Please check the logs for details.") 