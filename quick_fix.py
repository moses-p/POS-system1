"""
Quick fix for indentation issues in app.py
"""
import shutil
import py_compile

# Make a backup
shutil.copy('app.py', 'app.py.quick_backup')
print("Backup created: app.py.quick_backup")

# Read file content
with open('app.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Fix 1: create_order function indentation for if/else blocks
content = content.replace(
    "if order_id:\n                # Get the order using our resilient function\n            order = get_order_by_id(order_id)\n            if order:",
    "if order_id:\n                # Get the order using our resilient function\n                order = get_order_by_id(order_id)\n                if order:"
)

# Fix 2: create_order function else block
content = content.replace(
    "else:\n                    # If we can't get the order, return a generic success message",
    "                else:\n                    # If we can't get the order, return a generic success message"
)

# Fix 3: Exception handling in create_order
content = content.replace(
    "except Exception as e:\n        db.session.rollback()\n        logger.error(f\"Error creating order: {str(e)}\")\n            return None",
    "except Exception as e:\n        db.session.rollback()\n        logger.error(f\"Error creating order: {str(e)}\")\n        return None"
)

# Fix 4: catch_all route try-except block
content = content.replace(
    "try:\n                # Check if file exists in static folder\n                filepath = os.path.join(app.static_folder, path)\n                if os.path.exists(filepath) and os.path.isfile(filepath):\n                    return send_from_directory(app.static_folder, path)\n    except Exception as e:",
    "try:\n                # Check if file exists in static folder\n                filepath = os.path.join(app.static_folder, path)\n                if os.path.exists(filepath) and os.path.isfile(filepath):\n                    return send_from_directory(app.static_folder, path)\n            except Exception as e:"
)

# Fix 5: get_order_by_id function try-except blocks
content = content.replace(
    "try:\n            # Direct database query with LEFT JOIN to handle missing products\n        conn = sqlite3.connect('instance/pos.db')",
    "try:\n            # Direct database query with LEFT JOIN to handle missing products\n            conn = sqlite3.connect('instance/pos.db')"
)

# Fix 6: get_order_by_id return None indentation
content = content.replace(
    "if not order_row:\n                conn.close()\n                logger.error(f\"Order {order_id} not found in direct SQL\")\n            return None",
    "if not order_row:\n                conn.close()\n                logger.error(f\"Order {order_id} not found in direct SQL\")\n                return None"
)

# Fix 7: Inner exception handling in get_order_by_id
content = content.replace(
    "except Exception as inner_e:\n            logger.error(f\"Error in direct SQL retrieval: {str(inner_e)}\")\n            return None\n        \n    except Exception as e:",
    "except Exception as inner_e:\n                logger.error(f\"Error in direct SQL retrieval: {str(inner_e)}\")\n                return None\n        \n        except Exception as e:"
)

# Write the fixed content
with open('app.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("Applied fixes to app.py")

# Verify syntax
try:
    py_compile.compile('app.py', doraise=True)
    print("Syntax verification successful!")
except py_compile.PyCompileError as e:
    print(f"Syntax errors still exist: {str(e)}")
    print("Restoring from backup...")
    shutil.copy('app.py.quick_backup', 'app.py')
    print("Original file restored") 