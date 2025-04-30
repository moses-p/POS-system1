"""
Manually fix the app.py file by directly editing it
"""
import os
import shutil

# Make a backup first
shutil.copy('app.py', 'app.py.manual_backup')
print(f"Backup created: app.py.manual_backup")

# Read the entire file
with open('app.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Check for specific error patterns and fix them

# Fix 1: create_order function indentation for the condition "if order_id:"
content = content.replace(
    "if order_id:\n                # Get the order using our resilient function\n            order = get_order_by_id(order_id)\n            if order:",
    "if order_id:\n                # Get the order using our resilient function\n                order = get_order_by_id(order_id)\n                if order:"
)

# Fix 2: catch_all route try-except block
content = content.replace(
    "try:\n                # Check if file exists in static folder\n                filepath = os.path.join(app.static_folder, path)\n                if os.path.exists(filepath) and os.path.isfile(filepath):\n                    return send_from_directory(app.static_folder, path)\n    except Exception as e:",
    "try:\n                # Check if file exists in static folder\n                filepath = os.path.join(app.static_folder, path)\n                if os.path.exists(filepath) and os.path.isfile(filepath):\n                    return send_from_directory(app.static_folder, path)\n            except Exception as e:"
)

# Fix 3: get_order_by_id conn.close() indentation
content = content.replace(
    "if not order_row:\n                conn.close()\n                logger.error(f\"Order {order_id} not found in direct SQL\")\n            return None",
    "if not order_row:\n                conn.close()\n                logger.error(f\"Order {order_id} not found in direct SQL\")\n                return None"
)

# Fix 4: Exception blocks
content = content.replace(
    "except Exception as e:\n        db.session.rollback()\n        logger.error(f\"Error creating order: {str(e)}\")\n            return None, f\"Error creating order: {str(e)}\"",
    "except Exception as e:\n        db.session.rollback()\n        logger.error(f\"Error creating order: {str(e)}\")\n        return None, f\"Error creating order: {str(e)}\""
)

# Fix 5: Exception blocks in get_order_by_id
content = content.replace(
    "except Exception as inner_e:\n            logger.error(f\"Error in direct SQL retrieval: {str(inner_e)}\")\n            return None\n        \n    except Exception as e:\n        logger.error(f\"Error in get_order_by_id: {str(e)}\")\n        return None",
    "except Exception as inner_e:\n                logger.error(f\"Error in direct SQL retrieval: {str(inner_e)}\")\n                return None\n        \n        except Exception as e:\n            logger.error(f\"Error in get_order_by_id: {str(e)}\")\n            return None"
)

# Write the fixed content back to the file
with open('app.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("Fixed indentation issues in app.py")

# Verify syntax
try:
    import py_compile
    py_compile.compile('app.py', doraise=True)
    print("Syntax verification successful: app.py is now syntactically correct")
except py_compile.PyCompileError as e:
    print(f"Syntax errors still exist: {str(e)}")
    print("Restoring backup...")
    shutil.copy('app.py.manual_backup', 'app.py')
    print("Original file restored") 