@echo off
echo Building Standalone POS System Distribution...
echo This will create a complete package that works both online and offline.

REM Clean previous build if any
echo Cleaning previous build...
if exist "dist\POS System" rmdir /s /q "dist\POS System"
if exist "build" rmdir /s /q "build"

REM Run PyInstaller
echo Running PyInstaller...
python -m PyInstaller --onefile --windowed ^
    --hidden-import=eventlet.hubs.epolls ^
    --hidden-import=eventlet.hubs.kqueue ^
    --hidden-import=eventlet.hubs.selects ^
    --hidden-import=eventlet.hubs.polls ^
    --hidden-import=dns ^
    --hidden-import=dns.rdtypes ^
    --hidden-import=dns.rdtypes.ANY ^
    --hidden-import=dns.rdtypes.IN ^
    --hidden-import=dns.rdatatype ^
    --hidden-import=dns.rdataclass ^
    --hidden-import=dns.name ^
    --hidden-import=dns.exception ^
    --hidden-import=dns.inet ^
    --hidden-import=dns.ipv4 ^
    --hidden-import=dns.ipv6 ^
    --hidden-import=dns.resolver ^
    --hidden-import=dns.query ^
    --hidden-import=dns.dnssec ^
    --hidden-import=dns.zone ^
    --hidden-import=dns.message ^
    --hidden-import=dns.tsigkeyring ^
    --hidden-import=dns.update ^
    --hidden-import=dns.tsig ^
    --hidden-import=dns.e164 ^
    --hidden-import=dns.reversename ^
    --hidden-import=dns.tokenizer ^
    --hidden-import=dns.asyncquery ^
    --hidden-import=dns.asyncresolver ^
    --hidden-import=dns.namedict ^
    --hidden-import=dns._compat ^
    --hidden-import=dns._asyncbackend ^
    --hidden-import=dns._socket ^
    --hidden-import=dns._udp ^
    --hidden-import=dns._tcp ^
    --hidden-import=dns._tls ^
    --hidden-import=dns._http ^
    --hidden-import=dns._https ^
    --hidden-import=dns._network ^
    --hidden-import=dns._version ^
    --hidden-import=dns._immutable ^
    --hidden-import=dns._python ^
    --hidden-import=dns._dnssec ^
    --hidden-import=dns._edns ^
    --hidden-import=dns._rdata ^
    --hidden-import=dns._rrset ^
    --hidden-import=dns._tokenizer ^
    --hidden-import=dns._tsig ^
    --hidden-import=dns._update ^
    --hidden-import=dns._wiredata ^
    --hidden-import=dns._zone ^
    --name "POS System" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "instance;instance" ^
    --add-data "migrations;migrations" ^
    --add-data ".env;." ^
    --add-data "check_and_init_db.py;." ^
    --add-data "Install.bat;." ^
    pos_launcher.py

REM Create distribution directory if it doesn't exist
if not exist "dist\POS System" mkdir "dist\POS System"

REM Copy the Install.bat file to the distribution folder
echo Copying installation script...
copy "Install.bat" "dist\POS System\Install.bat" >nul

REM Create offline template
echo Creating offline templates...
if not exist "dist\POS System\templates" mkdir "dist\POS System\templates"
copy "templates\offline.html" "dist\POS System\templates\offline.html" >nul

REM Copy service worker and manifest
echo Copying service worker and manifest files...
if not exist "dist\POS System\static" mkdir "dist\POS System\static"
copy "static\service-worker.js" "dist\POS System\static\service-worker.js" >nul
copy "static\manifest.json" "dist\POS System\static\manifest.json" >nul

REM Create additional helper files
echo @echo off > "dist\POS System\Reset Database.bat"
echo echo This will reset the POS System database. All data will be lost! >> "dist\POS System\Reset Database.bat"
echo echo. >> "dist\POS System\Reset Database.bat"
echo set /p CONFIRM=Are you sure you want to continue? (Y/N): >> "dist\POS System\Reset Database.bat"
echo if /i "%%CONFIRM%%" neq "Y" goto :END >> "dist\POS System\Reset Database.bat"
echo echo Resetting database... >> "dist\POS System\Reset Database.bat"
echo if exist "instance\pos.db" del "instance\pos.db" >> "dist\POS System\Reset Database.bat"
echo "POS System.exe" --init-db >> "dist\POS System\Reset Database.bat"
echo echo Database has been reset. >> "dist\POS System\Reset Database.bat"
echo :END >> "dist\POS System\Reset Database.bat"
echo pause >> "dist\POS System\Reset Database.bat"

REM Create README with instructions
echo Creating README...
echo POS System > "dist\POS System\README.txt"
echo ========== >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo This POS System works both online and offline. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Installation: >> "dist\POS System\README.txt"
echo 1. Run Install.bat to install shortcuts and initialize the database. >> "dist\POS System\README.txt"
echo 2. Use the desktop or Start Menu shortcut to launch the application. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Offline Mode: >> "dist\POS System\README.txt"
echo - The system will automatically switch to offline mode when no internet connection is available. >> "dist\POS System\README.txt"
echo - Orders created in offline mode will be synchronized when back online. >> "dist\POS System\README.txt"
echo. >> "dist\POS System\README.txt"
echo Default Login: >> "dist\POS System\README.txt"
echo Username: admin >> "dist\POS System\README.txt"
echo Password: admin123 >> "dist\POS System\README.txt"

echo.
echo Build completed! The standalone distribution is in the "dist\POS System" folder.
echo This version works both online and offline.
echo.
pause 