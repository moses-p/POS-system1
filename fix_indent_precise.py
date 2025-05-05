def analyze_and_fix_indentation():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Examine 5 lines before the problematic area to determine correct indentation pattern
    start_index = max(0, 1035 - 5 - 1)  # 5 lines before line 1035, adjust for 0-indexing
    problem_area = lines[start_index:1037+10]  # Get several lines around the problem
    
    # Analyze indentation pattern
    indent_patterns = []
    for i, line in enumerate(problem_area):
        if line.strip():
            # Calculate the indentation level by counting leading spaces
            indent = len(line) - len(line.lstrip())
            indent_patterns.append((indent, line.strip(), start_index + i + 1))
    
    print("Current indentation patterns:")
    for indent, content, line_num in indent_patterns:
        print(f"Line {line_num}: {indent} spaces - {content[:40]}...")
    
    # Fix the specific lines with proper indentation
    if_line_index = 1035 - 1
    try_line_index = 1037 - 1
    
    # Determine the appropriate indentation level for this code block
    # The if statement appears to be at level 8, so try should be at level 12
    lines[try_line_index] = ' ' * 12 + 'try:\n'
    
    # Fix all the lines in the if block to have consistent indentation
    # First, fix lines in the try block (nested inside if)
    for i in range(try_line_index + 1, len(lines)):
        # Stop when we hit the except statement
        if 'except Exception as calc_err:' in lines[i]:
            lines[i] = ' ' * 12 + 'except Exception as calc_err:\n'
            break
        
        # Indent non-empty lines
        if lines[i].strip():
            lines[i] = ' ' * 16 + lines[i].lstrip()
    
    # Then fix the except block
    except_index = None
    for i in range(try_line_index, len(lines)):
        if 'except Exception as calc_err:' in lines[i]:
            except_index = i
            break
    
    if except_index is not None:
        # Fix indentation in the except block
        for i in range(except_index + 1, len(lines)):
            # Stop when we find the nested try
            if 'try:' in lines[i].strip():
                lines[i] = ' ' * 16 + 'try:\n'
                break
            
            # Indent non-empty lines in the except block
            if lines[i].strip():
                lines[i] = ' ' * 16 + lines[i].lstrip()
        
        # Find the nested try/except
        nested_try_index = None
        for i in range(except_index, len(lines)):
            if 'try:' in lines[i].strip() and i > except_index:
                nested_try_index = i
                break
        
        if nested_try_index is not None:
            # Fix indentation in the nested try block
            for i in range(nested_try_index + 1, len(lines)):
                # Stop at the nested except
                if 'except:' in lines[i].strip():
                    lines[i] = ' ' * 16 + 'except:\n'
                    nested_except_index = i
                    break
                
                # Indent non-empty lines in the nested try block
                if lines[i].strip():
                    lines[i] = ' ' * 20 + lines[i].lstrip()
            
            # Find and fix the nested except block
            nested_except_index = None
            for i in range(nested_try_index, len(lines)):
                if 'except:' in lines[i].strip():
                    nested_except_index = i
                    break
            
            if nested_except_index is not None:
                # Fix indentation in the nested except block
                for i in range(nested_except_index + 1, len(lines)):
                    # Stop when we reach customer_info block or return statement
                    if 'customer_info' in lines[i] or 'return render_template' in lines[i]:
                        break
                    
                    # Indent non-empty lines in the nested except block
                    if lines[i].strip():
                        lines[i] = ' ' * 20 + lines[i].lstrip()
    
    # Fix the customer_info block indentation
    customer_block_start = None
    for i in range(try_line_index, len(lines)):
        if 'customer_info' in lines[i]:
            customer_block_start = i
            break
    
    if customer_block_start is not None:
        # Set proper indentation for customer_info block
        for i in range(customer_block_start, customer_block_start + 7):
            if i < len(lines) and lines[i].strip():
                if i == customer_block_start:
                    lines[i] = ' ' * 16 + lines[i].lstrip()
                else:
                    # Indent the values in the dictionary
                    lines[i] = ' ' * 20 + lines[i].lstrip()
        
        # Fix the closing bracket and the return line
        for i in range(customer_block_start + 7, customer_block_start + 12):
            if i < len(lines) and 'return render_template' in lines[i]:
                lines[i] = ' ' * 12 + lines[i].lstrip()
                break
            elif i < len(lines) and lines[i].strip() == '}':
                lines[i] = ' ' * 16 + lines[i].lstrip()
    
    # Write the fixed content back
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed indentation issues with precise pattern matching")

if __name__ == "__main__":
    analyze_and_fix_indentation() 