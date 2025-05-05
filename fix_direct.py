def fix_specific_line():
    # This directly fixes the indentation issue on line 1037 where the try block
    # should be indented under the if statement on line 1035
    
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Look at line 1035 (index 1034) which has the if statement
    # and line 1037 (index 1036) which has the problematic try statement
    
    # Line numbers in error message are 1-indexed, but list is 0-indexed
    if_line_index = 1035 - 1
    try_line_index = 1037 - 1
    
    # Verify we have the correct lines
    if_line = lines[if_line_index].strip()
    try_line = lines[try_line_index].strip()
    
    if 'if request.method == \'GET\':' in if_line and 'try:' in try_line:
        # Fix the indentation on the try line
        lines[try_line_index] = ' ' * 12 + 'try:\n'
        
        # Fix indentation for all lines in the try block until we hit except
        current_index = try_line_index + 1
        while current_index < len(lines) and 'except' not in lines[current_index]:
            if lines[current_index].strip():
                lines[current_index] = ' ' * 16 + lines[current_index].lstrip()
            current_index += 1
        
        # Fix the except line's indentation
        if current_index < len(lines) and 'except' in lines[current_index]:
            lines[current_index] = ' ' * 12 + lines[current_index].lstrip()
            
            # Fix indentation for the except block
            except_block_index = current_index + 1
            while except_block_index < len(lines) and 'try:' not in lines[except_block_index]:
                if lines[except_block_index].strip():
                    lines[except_block_index] = ' ' * 16 + lines[except_block_index].lstrip()
                except_block_index += 1
            
            # If we find another try in the except block, fix its indentation too
            if except_block_index < len(lines) and 'try:' in lines[except_block_index]:
                lines[except_block_index] = ' ' * 16 + 'try:\n'
                
                # Fix indent for the nested try block
                nested_try_index = except_block_index + 1
                while nested_try_index < len(lines) and 'except:' not in lines[nested_try_index]:
                    if lines[nested_try_index].strip():
                        lines[nested_try_index] = ' ' * 20 + lines[nested_try_index].lstrip()
                    nested_try_index += 1
                
                # Fix the nested except line
                if nested_try_index < len(lines) and 'except:' in lines[nested_try_index]:
                    lines[nested_try_index] = ' ' * 16 + 'except:\n'
                    
                    # Fix indentation for the nested except block
                    nested_except_index = nested_try_index + 1
                    # Continue until we hit something that indicates the end of this block
                    while nested_except_index < len(lines) and 'customer_info' not in lines[nested_except_index]:
                        if lines[nested_except_index].strip():
                            lines[nested_except_index] = ' ' * 20 + lines[nested_except_index].lstrip()
                        nested_except_index += 1
    
    # Write the fixed content
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed indentation issue at line 1037")

if __name__ == "__main__":
    fix_specific_line() 