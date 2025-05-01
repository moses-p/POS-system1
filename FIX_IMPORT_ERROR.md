# Fix for "ImportError: cannot import name 'app' from 'app'"

## Problem

During installation or startup of the POS System, the following error might occur:

```
Traceback (most recent call last):
  File "pos_launcher.py", line 7, in <module>
ImportError: cannot import name 'app' from 'app'
[PYI-16280:ERROR] Failed to execute script 'pos_launcher' due to unhandled exception!
```

This error happens because the PyInstaller bundle is missing a proper `app.py` file that exports the necessary components.

## Quick Fix

1. **Use the provided rebuild script**:
   - Run `rebuild_standalone.bat` to recompile the application with the fixed app.py file.
   - The script will automatically reinstall the application with the corrected components.

## Manual Fix

If the rebuild script doesn't work, you can manually fix the issue:

1. **Create or update app.py**:
   - Ensure app.py contains all required components (Flask app instance, database models, etc.)
   - The updated app.py should export `app` and `init_db` functions that are imported by pos_launcher.py

2. **Rebuild the PyInstaller bundle**:
   ```
   pip install pyinstaller
   pyinstaller --onefile --windowed --icon=ag_logo.ico --add-data "templates;templates" --add-data "static;static" --name "POS System" pos_launcher.py
   ```

3. **Copy additional files to the distribution**:
   ```
   xcopy /E /I /Y static "dist\POS System\static"
   xcopy /E /I /Y templates "dist\POS System\templates"
   copy /Y *.bat "dist\POS System\"
   copy /Y *.md "dist\POS System\"
   copy /Y *.ico "dist\POS System\"
   copy /Y README.txt "dist\POS System\"
   ```

## Contact Information

If you need further assistance with this issue:

- **Email:** arisegeniusug@gmail.com
- **Phone:** +256743232445 