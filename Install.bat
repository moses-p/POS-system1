@echo off
echo Installing POS System...
echo.

REM Create desktop shortcut
echo Creating desktop shortcut...
set SCRIPT="%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\POS System.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0POS System.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Point of Sale System" >> %SCRIPT%
echo oLink.IconLocation = "%~dp0favicon.ico" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

REM Create Start Menu shortcut
echo Creating Start Menu shortcut...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\POS System" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\POS System"
set SCRIPT="%TEMP%\create_start_menu_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\POS System\POS System.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0POS System.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Point of Sale System" >> %SCRIPT%
echo oLink.IconLocation = "%~dp0favicon.ico" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

REM Ensure database is initialized
echo Initializing database...
"%~dp0POS System.exe" --init-db

echo.
echo Installation completed!
echo You can run the application from the desktop shortcut or Start Menu.
echo.
pause 