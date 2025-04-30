import shutil
import py_compile

# Make a backup
backup_file = 'app.py.line_backup'
shutil.copy('app.py', backup_file)
print(f"Created backup at {backup_file}")

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Target exactly line 3213 (index 3212)
line_index = 3212
fixed = False

if len(lines) > line_index and 'cursor.execute("""' in lines[line_index]:
    # Fix the indentation on this line and the following SQL query lines
    # Assume we want 12 spaces (3 indentation levels x 4 spaces)
    target_indent = 12
    
    # Fix up to the next 10 lines or until we find the closing """
    for i in range(line_index, min(line_index + 10, len(lines))):
        # Fix the indentation
        lines[i] = ' ' * target_indent + lines[i].lstrip()
        
        if '"""' in lines[i] and i > line_index:  # Found the end of the SQL query
            fixed = True
            print(f"Fixed indentation from line {line_index+1} to {i+1}")
            break
            
    if not fixed and line_index + 10 >= len(lines):
        fixed = True  # Assume we fixed it even if we didn't find the closing """
        print(f"Fixed indentation starting at line {line_index+1}")

# Write the fixed content
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Verify syntax
try:
    py_compile.compile('app.py', doraise=True)
    print("Syntax check passed! The file has been fixed.")
except py_compile.PyCompileError as e:
    print(f"Syntax errors still exist: {str(e)}")
    print("Restoring backup...")
    shutil.copy(backup_file, 'app.py')
    print("Original file restored")

if fixed:
    print("Indentation error at line 3213 has been fixed.")
else:
    print("Could not find the error at line 3213. Manual inspection needed.") 