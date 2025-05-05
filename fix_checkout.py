def fix_indentation():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the problematic line
    found_if = False
    found_calc = False
    
    for i, line in enumerate(lines):
        if 'if request.method == \'GET\':' in line:
            found_if = True
            if_index = i
        elif found_if and '# Calculate total for display' in line:
            found_calc = True
            calc_index = i
        elif found_if and found_calc and 'try:' in line:
            # Found the try statement that needs indentation
            lines[i] = '                try:\n'
            # Fix other indentation issues in this block
            for j in range(i+1, len(lines)):
                if lines[j].strip() and not lines[j].startswith('                ') and 'except Exception as calc_err:' not in lines[j]:
                    lines[j] = '                    ' + lines[j].lstrip()
                if 'except Exception as calc_err:' in lines[j]:
                    lines[j] = '                except Exception as calc_err:\n'
                    # Fix indentation for the except block
                    for k in range(j+1, len(lines)):
                        if lines[k].strip() and not lines[k].startswith('                    '):
                            if 'try:' in lines[k]:
                                lines[k] = '                        try:\n'
                            elif 'except:' in lines[k]:
                                lines[k] = '                        except:\n'
                            else:
                                lines[k] = '                    ' + lines[k].lstrip()
                        if 'customer_info =' in lines[k]:
                            break
                    break
            break
    
    # Write the fixed file
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed indentation in checkout function")

if __name__ == "__main__":
    fix_indentation() 