@echo off
echo Creating POS System distribution package...

REM Create distribution directory
mkdir dist 2>nul
mkdir "dist\POS System" 2>nul
mkdir "dist\POS System\templates" 2>nul
mkdir "dist\POS System\static" 2>nul
mkdir "dist\POS System\instance" 2>nul

REM Copy core files
echo Copying core application files...
copy app.py "dist\POS System\" >nul
copy pos_launcher.py "dist\POS System\" >nul
copy check_and_init_db.py "dist\POS System\" >nul
copy fix_reference_number.py "dist\POS System\" >nul
copy sql_operations.py "dist\POS System\" >nul
copy Install.bat "dist\POS System\" >nul

REM Copy templates
echo Copying templates...
xcopy /s /i templates "dist\POS System\templates" >nul

REM Copy static files
echo Copying static files...
xcopy /s /i static "dist\POS System\static" >nul

REM Create README
echo Creating documentation...
echo POS System > "dist\POS System\README.txt"
echo ========== >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo This POS System works both online and offline. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Installation: >> "dist\POS System\README.txt"
echo 1. Make sure Python 3.8+ and required packages are installed. >> "dist\POS System\README.txt"
echo 2. Run Install.bat to install shortcuts and initialize the database. >> "dist\POS System\README.txt"
echo 3. Use the desktop or Start Menu shortcut to launch the application. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Offline Mode: >> "dist\POS System\README.txt"
echo - The system will automatically switch to offline mode when no internet connection is available. >> "dist\POS System\README.txt"
echo - Orders created in offline mode will be synchronized when back online. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Default Login: >> "dist\POS System\README.txt"
echo Username: admin >> "dist\POS System\README.txt"
echo Password: admin123 >> "dist\POS System\README.txt"

REM Create requirements.txt
echo Creating requirements file...
echo flask==2.0.1 > "dist\POS System\requirements.txt"
echo flask-sqlalchemy==2.5.1 >> "dist\POS System\requirements.txt"
echo flask-login==0.5.0 >> "dist\POS System\requirements.txt"
echo flask-bcrypt==0.7.1 >> "dist\POS System\requirements.txt"
echo flask-migrate==3.1.0 >> "dist\POS System\requirements.txt"
echo flask-cors==3.0.10 >> "dist\POS System\requirements.txt"
echo pillow==8.3.1 >> "dist\POS System\requirements.txt"
echo qrcode==7.3.1 >> "dist\POS System\requirements.txt"
echo requests==2.26.0 >> "dist\POS System\requirements.txt"

REM Create startup script
echo Creating startup script...
echo @echo off > "dist\POS System\start.bat"
echo title POS System >> "dist\POS System\start.bat"
echo python pos_launcher.py >> "dist\POS System\start.bat"

echo.
echo Distribution package created in "dist\POS System".
echo To run the POS System:
echo 1. Navigate to "dist\POS System"
echo 2. Install required packages: pip install -r requirements.txt
echo 3. Run start.bat
echo.
pause 