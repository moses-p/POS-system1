"""
Direct line fix for app.py indentation issues
"""
import shutil
import sqlite3
import os
from datetime import datetime

# Make a backup
shutil.copy('app.py', 'app.py.direct_backup')
print("Backup created at app.py.direct_backup")

# Read the file
with open('app.py', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# Fix specific lines with indentation issues

# Fix 1: Line 2854-2856 (if order_id: block)
if len(lines) >= 2856:
    lines[2854] = "            if order_id:\n"
    lines[2855] = "                # Get the order using our resilient function\n"
    lines[2856] = "                order = get_order_by_id(order_id)\n"

# Fix 2: Line 2867-2868 (if/else block)
if len(lines) >= 2868:
    lines[2866] = "                if order:\n"
    lines[2867] = "                    return order, None\n"
    lines[2868] = "                else:\n"

# Fix 3: Line 2942-2944 (Exception block)
if len(lines) >= 2944:
    lines[2942] = "    except Exception as e:\n"
    lines[2943] = "        db.session.rollback()\n"
    lines[2944] = "        logger.error(f\"Error creating order: {str(e)}\")\n"
    if len(lines) > 2945:
        lines[2945] = "        return None, f\"Error creating order: {str(e)}\"\n"

# Fix 4: catch_all function
for i in range(2928, 2938):
    if i < len(lines) and 'try:' in lines[i] and i+4 < len(lines):
        lines[i] = "            try:\n"
        # Fix the exception line
        for j in range(i+1, i+10):
            if j < len(lines) and 'except Exception as e:' in lines[j]:
                lines[j] = "            except Exception as e:\n"
                break

# Fix 5: get_order_by_id function
for i in range(3100, 3140):
    if i < len(lines) and "try:" in lines[i] and "Direct database query" in lines[i+1]:
        lines[i] = "        try:\n"
        # Also fix the except line
        for j in range(i+20, i+40):
            if j < len(lines) and "except Exception as inner_e:" in lines[j]:
                lines[j] = "        except Exception as inner_e:\n"
                lines[j+1] = "            logger.error(f\"Error in direct SQL retrieval: {str(inner_e)}\")\n"
                lines[j+2] = "            return None\n"
                break
        break

# Write back the fixed file
with open('app.py', 'w', encoding='utf-8') as file:
    file.writelines(lines)

print("Direct line fixes applied to app.py")

# Verify the syntax
try:
    import py_compile
    py_compile.compile('app.py', doraise=True)
    print("Syntax verification successful")
except py_compile.PyCompileError as e:
    print(f"Syntax errors still exist: {str(e)}")
    print("Restoring from backup...")
    shutil.copy('app.py.direct_backup', 'app.py')
    print("Original file restored")

def fix_database():
    # Backup the database first
    if os.path.exists('instance/pos.db'):
        backup_file = f'instance/pos_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2('instance/pos.db', backup_file)
        print(f"Created backup at {backup_file}")

    # Connect to the database
    conn = sqlite3.connect('instance/pos.db')
    cursor = conn.cursor()

    try:
        # Fix negative stock values
        cursor.execute("UPDATE product SET stock = 0 WHERE stock < 0")
        print("Fixed negative stock values")

        # Delete orphaned records
        cursor.execute("DELETE FROM order_item WHERE order_id NOT IN (SELECT id FROM [order])")
        cursor.execute("DELETE FROM cart_item WHERE cart_id NOT IN (SELECT id FROM cart)")
        cursor.execute("DELETE FROM stock_movement WHERE product_id NOT IN (SELECT id FROM product)")
        print("Cleaned up orphaned records")

        # Commit changes
        conn.commit()
        print("Database fixes applied successfully!")

    except Exception as e:
        print(f"Error fixing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting direct database fix...")
    fix_database()
    print("Database fix completed!") 