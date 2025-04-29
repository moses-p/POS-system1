@echo off
echo Building POS System Installer...

REM Make sure check_and_init_db.py is included
python -m PyInstaller pos_app.spec --noconfirm

REM Copy the Install.bat file to the distribution folder
echo Copying installation script...
copy "dist\POS System\Install.bat" "dist\POS System\Install.bat" >nul

echo.
echo Build complete! The executable is in the "dist\POS System" folder.
echo You can distribute this folder to install on other computers.
pause 