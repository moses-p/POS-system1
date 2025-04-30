import shutil
import re
import py_compile

# Make a backup
backup_file = 'app.py.indent_backup'
shutil.copy('app.py', backup_file)
print(f"Created backup at {backup_file}")

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the problematic area around line 3213
# Look for a pattern like:
# cursor.execute("""
fixed = False
for i in range(max(0, 3200), min(len(lines), 3250)):
    if 'cursor.execute("""' in lines[i] and lines[i].startswith(' ' * 12):  # If it has too much indentation
        # Correct the indentation to 4 spaces per level (assuming it should be at level 3)
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        correct_indent = 12  # 3 levels * 4 spaces
        
        if current_indent > correct_indent:
            # Fix this line and the next few SQL query lines
            for j in range(i, min(i + 10, len(lines))):
                if '"""' in lines[j]:  # End of the SQL query
                    # Fix this line too
                    lines[j] = ' ' * correct_indent + lines[j].lstrip()
                    break
                lines[j] = ' ' * correct_indent + lines[j].lstrip()
            
            fixed = True
            print(f"Fixed indentation at lines {i}-{j}")
            break

if fixed:
    # Write the fixed file
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Verify the fix
    try:
        py_compile.compile('app.py', doraise=True)
        print("Syntax check passed! The fix was successful.")
    except py_compile.PyCompileError as e:
        print(f"Syntax error still exists: {e}")
        print("Restoring backup...")
        shutil.copy(backup_file, 'app.py')
        print("Backup restored")
else:
    print("Could not find the problematic line to fix automatically.")
    print("You may need to manually edit the file or try a different approach.") 