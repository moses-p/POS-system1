@echo off
echo ===================================
echo Rebuilding POS System Standalone...
echo ===================================

echo Installing PyInstaller if not present...
pip install pyinstaller

echo Compiling the application...
pyinstaller --onefile --windowed --icon=ag_logo.ico --add-data "templates;templates" --add-data "static;static" --name "POS System" pos_launcher.py

echo Copying additional files to distribution...
mkdir "dist\POS System"
mkdir "dist\POS System\static"
mkdir "dist\POS System\templates"
mkdir "dist\POS System\instance"

xcopy /E /I /Y static "dist\POS System\static"
xcopy /E /I /Y templates "dist\POS System\templates"
copy /Y *.bat "dist\POS System\"
copy /Y *.md "dist\POS System\"
copy /Y *.ico "dist\POS System\"
copy /Y README.txt "dist\POS System\"

echo ===================================
echo Build completed!
echo ===================================
echo POS System has been rebuilt with the fixed app.py file.
echo The standalone executable is located in the dist folder.
echo.
echo Press any key to exit...
pause > nul 