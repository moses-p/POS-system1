import re
import sys

def fix_indentation_errors(filename='app.py'):
    # Read the entire file
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Create a backup
    with open(f'{filename}.bak', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Fixes to apply:
    
    # 1. Fix lines 958-959 (if order block)
    if len(lines) >= 959:
        if 'if order:' in lines[957] and 'return redirect' in lines[958]:
            # Fix indentation for the if block
            lines[958] = ' ' * 24 + lines[958].lstrip()
    
    # 2. Fix print_receipt function (lines 995-1019)
    try_found = False
    try_idx = 0
    for i, line in enumerate(lines):
        if '@app.route(\'/receipt/<int:order_id>\')' in line:
            # Found the print_receipt function
            for j in range(i+1, i+30):  # Look ahead for the try statement
                if 'try:' in lines[j]:
                    try_found = True
                    try_idx = j
                    break
            
            if try_found:
                # Check for missing except clause and fix it
                except_found = False
                for j in range(try_idx+1, try_idx+30):
                    if j >= len(lines):
                        break
                    if 'except ' in lines[j]:
                        except_found = True
                        break
                
                if not except_found:
                    # Find the return statement and add except after it
                    for j in range(try_idx+1, try_idx+30):
                        if j >= len(lines):
                            break
                        if 'return render_template' in lines[j]:
                            indent_level = len(lines[j]) - len(lines[j].lstrip())
                            # Add except block after the return
                            except_block = ' ' * 4 + 'except Exception as e:\n'
                            except_block += ' ' * 8 + 'logger.error(f"Error loading receipt for order {order_id}: {str(e)}")\n'
                            except_block += ' ' * 8 + 'flash(f"Error loading receipt: {str(e)}", \'error\')\n'
                            except_block += ' ' * 8 + 'return redirect(url_for(\'index\'))\n'
                            
                            lines.insert(j+1, except_block)
                            break
    
    # 3. Fix order_confirmation function (lines around 1022-1047)
    for i, line in enumerate(lines):
        if '@app.route(\'/order/<int:order_id>\')' in line or 'def order_confirmation(' in line:
            # Find the try statement
            try_idx = 0
            for j in range(i, i+10):
                if j >= len(lines):
                    break
                if 'try:' in lines[j]:
                    try_idx = j
                    break
            
            if try_idx > 0:
                # Fix indentation for the 'abort(403)' line
                for j in range(try_idx, try_idx+20):
                    if j >= len(lines):
                        break
                    if 'abort(403)' in lines[j]:
                        lines[j] = ' ' * 12 + 'abort(403)\n'
                
                # Fix indentation for the return statement
                for j in range(try_idx, try_idx+20):
                    if j >= len(lines):
                        break
                    if 'return render_template' in lines[j] and not lines[j].startswith(' '):
                        lines[j] = ' ' * 8 + lines[j]
                
                # Remove duplicate except blocks
                except_indices = []
                for j in range(try_idx, try_idx+20):
                    if j >= len(lines):
                        break
                    if 'except Exception as e:' in lines[j] and j > try_idx:
                        except_indices.append(j)
                
                # Remove duplicates from the end
                for j in reversed(except_indices[1:]):
                    for k in range(j, j+4):  # Remove the except block (4 lines)
                        if k < len(lines):
                            lines[k] = ''
    
    # 4. Fix create_order function (lines around 2708-2797)
    for i, line in enumerate(lines):
        if 'def create_order(' in line:
            # Find the try statements
            nested_try_idx = 0
            for j in range(i+1, i+100):
                if j >= len(lines):
                    break
                if '# Skip SQLAlchemy entirely and use direct SQL' in lines[j]:
                    # Next line should be try:
                    if j+1 < len(lines) and 'try:' in lines[j+1]:
                        nested_try_idx = j+1
                        break
            
            if nested_try_idx > 0:
                # Fix indentation for cursor declaration
                for j in range(nested_try_idx, nested_try_idx+20):
                    if j >= len(lines):
                        break
                    if 'cursor = conn.cursor()' in lines[j]:
                        lines[j] = ' ' * 12 + lines[j].lstrip()
                
                # Fix indentation for INSERT INTO statements
                for j in range(nested_try_idx, nested_try_idx+50):
                    if j >= len(lines):
                        break
                    if 'INSERT INTO [order]' in lines[j]:
                        indent_level = ' ' * 12
                        for k in range(j, j+20):
                            if k >= len(lines):
                                break
                            if '"""' in lines[k]:
                                lines[k] = indent_level + lines[k].lstrip()
                
                # Fix indentation for loop over items_data
                for j in range(nested_try_idx, nested_try_idx+100):
                    if j >= len(lines):
                        break
                    if 'for item_data in items_data:' in lines[j]:
                        lines[j] = ' ' * 12 + lines[j].lstrip()
                        # Indent the block inside the loop
                        for k in range(j+1, j+20):
                            if k >= len(lines):
                                break
                            if len(lines[k].strip()) > 0 and not lines[k].strip().startswith('#'):
                                lines[k] = ' ' * 16 + lines[k].lstrip()
                
                # Fix 'Commit the transaction' indentation
                for j in range(nested_try_idx+50, nested_try_idx+150):
                    if j >= len(lines):
                        break
                    if '# Commit the transaction' in lines[j]:
                        lines[j] = ' ' * 12 + lines[j].lstrip()
                        lines[j+1] = ' ' * 12 + lines[j+1].lstrip()
                        lines[j+2] = ' ' * 12 + lines[j+2].lstrip()
                
                # Fix 'Return the created order' indentation
                for j in range(nested_try_idx+50, nested_try_idx+150):
                    if j >= len(lines):
                        break
                    if '# Return the created order' in lines[j]:
                        lines[j] = ' ' * 12 + lines[j].lstrip()
                        lines[j+1] = ' ' * 12 + lines[j+1].lstrip()
                        lines[j+2] = ' ' * 12 + lines[j+2].lstrip()
                        lines[j+3] = ' ' * 12 + lines[j+3].lstrip()
                        # Fix if-else indentation
                        lines[j+4] = ' ' * 16 + lines[j+4].lstrip()
                        lines[j+5] = ' ' * 16 + lines[j+5].lstrip()
                        lines[j+6] = ' ' * 16 + lines[j+6].lstrip()
    
                # Fix except block indentation
                for j in range(nested_try_idx+100, nested_try_idx+200):
                    if j >= len(lines):
                        break
                    if 'except Exception as e:' in lines[j]:
                        lines[j] = ' ' * 8 + lines[j].lstrip()
                        # Fix the content of the except block
                        for k in range(j+1, j+10):
                            if k >= len(lines):
                                break
                            if 'logger.error' in lines[k] or 'if \'conn\'' in lines[k]:
                                lines[k] = ' ' * 12 + lines[k].lstrip()
                            elif 'conn.rollback()' in lines[k] or 'conn.close()' in lines[k]:
                                lines[k] = ' ' * 16 + lines[k].lstrip()
                            elif 'return None,' in lines[k]:
                                lines[k] = ' ' * 12 + lines[k].lstrip()
    
    # Write the fixed file
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Fixed indentation errors in {filename}")
    print(f"Backup saved to {filename}.bak")

if __name__ == "__main__":
    fix_indentation_errors() 