def fix_specific_indentation():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix the specific indentation error at line 1037
    # "expected an indented block after 'if' statement on line 1035"
    
    # Examining approximately 10 lines before and after the problematic line
    start_line = max(1025, 1037 - 10)
    end_line = min(len(lines), 1037 + 10)
    
    # Looking specifically for an 'if' statement followed by a 'try:' with wrong indentation
    for i in range(start_line, end_line):
        if i >= len(lines):
            break
            
        # Check if this is line 1035 with an 'if' statement
        if i == 1035 - 1:  # Adjust for 0-indexing
            # The next 'try:' statement should be indented
            for j in range(i+1, i+10):
                if j >= len(lines):
                    break
                if 'try:' in lines[j] and not lines[j].startswith(' ' * 12):
                    # This is our problematic try statement - fix indentation
                    # If the try is at line 1037, it's j = 1037-1 (0-indexed)
                    # Properly indent the try statement and all lines in its block
                    lines[j] = ' ' * 12 + 'try:\n'
                    
                    # Fix indentation for the block inside this try
                    in_try_block = True
                    for k in range(j+1, len(lines)):
                        if 'except' in lines[k]:
                            # Found the except clause, fix its indentation too
                            lines[k] = ' ' * 12 + lines[k].lstrip()
                            break
                        elif '@app.route' in lines[k] or 'def ' in lines[k]:
                            # Reached the end of the function
                            break
                        elif lines[k].strip():
                            # Indent all non-empty lines in the try block
                            if not lines[k].startswith(' ' * 16):
                                lines[k] = ' ' * 16 + lines[k].lstrip()
    
    # Write the fixed content back to app.py
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed specific indentation error at line 1037")

if __name__ == "__main__":
    fix_specific_indentation() 