import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_sqlalchemy_models():
    """
    Update the Flask-SQLAlchemy models to match the database schema
    """
    try:
        # Import the Flask app to get its context
        from app import app, db
        
        with app.app_context():
            inspector = inspect(db.engine)
            
            # Get order table columns from the database
            order_columns = inspector.get_columns('order')
            order_column_names = [col['name'] for col in order_columns]
            
            logger.info(f"Database 'order' table columns: {order_column_names}")
            
            # Check for missing foreign key relationships
            fk_relationships = inspector.get_foreign_keys('order')
            logger.info(f"Foreign key relationships: {json.dumps([dict(fk) for fk in fk_relationships], indent=2)}")
            
            # Check the SQLAlchemy model
            from app import Order
            model_columns = Order.__table__.columns
            model_column_names = [col.name for col in model_columns]
            
            logger.info(f"SQLAlchemy model columns: {model_column_names}")
            
            missing_db_columns = set(model_column_names) - set(order_column_names)
            missing_model_columns = set(order_column_names) - set(model_column_names)
            
            logger.info(f"Missing from database: {missing_db_columns}")
            logger.info(f"Missing from model: {missing_model_columns}")
            
            # If there are any discrepancies, we need to address them
            if missing_db_columns or missing_model_columns:
                logger.warning("Discrepancies found between SQLAlchemy models and database schema!")
                
                # Option 1: Update database schema to match model
                # This is often risky if there's existing data
                
                # Option 2: Force SQLAlchemy to reload models from database
                # This is safer but temporary until code is updated
                
                if missing_model_columns:
                    logger.info("Recommend updating the Order model in app.py to include: " + 
                               ", ".join([f"{col}" for col in missing_model_columns]))
                
                if missing_db_columns:
                    logger.info("Recommend running fix_order_table.py to update database schema")
            else:
                logger.info("No discrepancies found between models and database schema!")
                
            # Check for any issues with direct SQL vs SQLAlchemy
            with db.engine.connect() as conn:
                # Test if direct SQL can create an order
                conn.execute(text("BEGIN TRANSACTION"))
                try:
                    # Test insert with minimal data (will be rolled back)
                    order_columns_sql = ", ".join(order_column_names)
                    placeholders = ", ".join(["NULL" for _ in order_column_names])
                    sql = f"INSERT INTO 'order' ({order_columns_sql}) VALUES ({placeholders})"
                    
                    # Replace some NULLs with values for non-nullable columns
                    sql = sql.replace("NULL", "'test'", 1)  # For a TEXT column
                    
                    # Check if total_amount is in the columns (it should be non-nullable)
                    if "total_amount" in order_column_names:
                        total_idx = order_column_names.index("total_amount")
                        parts = sql.split("NULL")
                        if len(parts) > total_idx + 1:
                            # Replace the NULL for total_amount with 0.0
                            sql = "NULL".join(parts[:total_idx+1]) + "0.0" + "NULL".join(parts[total_idx+1:])
                    
                    logger.info(f"Testing SQL: {sql}")
                    conn.execute(text(sql))
                    logger.info("Direct SQL insert test succeeded")
                except Exception as e:
                    logger.error(f"Direct SQL insert test failed: {str(e)}")
                finally:
                    conn.execute(text("ROLLBACK"))
                    
            return True
            
    except ImportError as e:
        logger.error(f"ImportError: {str(e)}")
        logger.error("Make sure you're running this script from the same directory as app.py")
        return False
    except Exception as e:
        logger.error(f"Error fixing SQLAlchemy models: {str(e)}")
        return False

if __name__ == "__main__":
    print("Checking SQLAlchemy models against database schema...")
    success = fix_sqlalchemy_models()
    if success:
        print("Check complete! See log for details.")
    else:
        print("Failed to check/fix models. See log for details.") 