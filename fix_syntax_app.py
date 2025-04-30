import re

def fix_create_order_function():
    with open('app.py', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find and fix the create_order function indentation
    create_order_pattern = r'def create_order\(.*?\):.*?try:.*?try:.*?except SQLAlchemyError as e:.*?if order_id:.*?order = get_order_by_id\(order_id\)'
    
    # Fix if/else indentation in create_order function
    content = re.sub(
        r'if order_id:(\s+)# Get the order using our resilient function\s+order = get_order_by_id\(order_id\)\s+if order:(\s+)return order, None\s+else:(\s+)# If we can\'t get the order, return a generic success message',
        r'if order_id:\n                # Get the order using our resilient function\n                order = get_order_by_id(order_id)\n                if order:\n                    return order, None\n                else:\n                    # If we can\'t get the order, return a generic success message',
        content, flags=re.DOTALL
    )
    
    # Fix the outer except block indentation
    content = re.sub(
        r'except Exception as e:(\s+)db\.session\.rollback\(\)\s+logger\.error\(f"Error creating order: \{str\(e\)\}"\)\s+return None, f"Error creating order: \{str\(e\)\}"',
        r'except Exception as e:\n        db.session.rollback()\n        logger.error(f"Error creating order: {str(e)}")\n        return None, f"Error creating order: {str(e)}"',
        content, flags=re.DOTALL
    )
    
    # Fix the catch_all route try-except block
    content = re.sub(
        r'try:(\s+)# Check if file exists in static folder(\s+)filepath = os\.path\.join\(app\.static_folder, path\)(\s+)if os\.path\.exists\(filepath\) and os\.path\.isfile\(filepath\):(\s+)return send_from_directory\(app\.static_folder, path\)(\s+)except Exception as e:',
        r'try:\n                # Check if file exists in static folder\n                filepath = os.path.join(app.static_folder, path)\n                if os.path.exists(filepath) and os.path.isfile(filepath):\n                    return send_from_directory(app.static_folder, path)\n            except Exception as e:',
        content, flags=re.DOTALL
    )
    
    # Fix the get_order_by_id function try-except block
    content = re.sub(
        r'try:(\s+)# Direct database query with LEFT JOIN to handle missing products(\s+)conn = sqlite3\.connect\(\'instance/pos\.db\'\)',
        r'try:\n            # Direct database query with LEFT JOIN to handle missing products\n            conn = sqlite3.connect(\'instance/pos.db\')',
        content, flags=re.DOTALL
    )
    
    # Fix order_row[0] indentation
    content = re.sub(
        r'if not order_row:(\s+)conn\.close\(\)(\s+)logger\.error\(f"Order \{order_id\} not found in direct SQL"\)',
        r'if not order_row:\n                conn.close()\n                logger.error(f"Order {order_id} not found in direct SQL")',
        content, flags=re.DOTALL
    )
    
    # Fix indentation of the except block in get_order_by_id
    content = re.sub(
        r'except Exception as inner_e:(\s+)logger\.error\(f"Error in direct SQL retrieval: \{str\(inner_e\)\}"\)(\s+)return None',
        r'except Exception as inner_e:\n            logger.error(f"Error in direct SQL retrieval: {str(inner_e)}")\n            return None',
        content, flags=re.DOTALL
    )
    
    with open('app_fixed.py', 'w', encoding='utf-8') as file:
        file.write(content)
    
    print("Fixed syntax issues and saved to app_fixed.py")

if __name__ == "__main__":
    fix_create_order_function() 