def fix_syntax_errors(filename="app.py"):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Create a simple backup
    with open(f"{filename}.syntax_backup", "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    # Create a clean app.py file
    with open("app.py.clean", "w", encoding="utf-8") as f:
        # Process the file line by line
        i = 0
        in_try_block = False
        while i < len(lines):
            line = lines[i]
            
            # Check for a try statement without except
            if "try:" in line.strip() and not in_try_block:
                in_try_block = True
                f.write(line)
            
            # Check for a return statement after try but before except
            elif in_try_block and "return" in line.strip() and "except" not in line:
                f.write(line)
                
                # Look for the next 'except' statement - if there is one directly after, skip it
                if i + 1 < len(lines) and "except" in lines[i + 1].strip():
                    # Skip the invalid except line
                    i += 1
                else:
                    # Add a simple except block if one is missing
                    indent = len(line) - len(line.lstrip())
                    f.write(" " * indent + "except Exception as e:\n")
                    f.write(" " * (indent + 4) + "logger.error(f\"Error: {str(e)}\")\n")
                    f.write(" " * (indent + 4) + "flash(f\"An error occurred: {str(e)}\", 'error')\n")
                    f.write(" " * (indent + 4) + "return redirect(url_for('index'))\n")
                
                in_try_block = False
            
            # Check for duplicate except blocks
            elif "except Exception as e:" in line and not line.strip().startswith("except"):
                # Skip this duplicate except block and its contents
                i += 1
                while i < len(lines) and len(lines[i].strip()) > 0 and (lines[i].strip().startswith("logger") or lines[i].strip().startswith("flash") or lines[i].strip().startswith("return")):
                    i += 1
                continue
            
            else:
                f.write(line)
            
            i += 1
    
    # Replace the original file with the cleaned version
    import os
    import shutil
    shutil.move("app.py.clean", filename)
    
    print(f"Fixed syntax errors in {filename}")
    print(f"Backup saved as {filename}.syntax_backup")

if __name__ == "__main__":
    fix_syntax_errors() 