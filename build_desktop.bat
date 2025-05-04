@echo off
REM Build script for POS System desktop packaging (Windows)

REM Step 1: Install dependencies
pip install -r requirements.txt

REM Step 2: Build the executable with PyInstaller
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" pos_launcher.py

REM Step 3: Notify user
if exist dist\pos_launcher.exe (
    echo Build successful! Find your executable in the dist directory.
) else (
    echo Build failed. Please check the output above for errors.
)

pause 