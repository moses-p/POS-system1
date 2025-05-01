@echo off
echo Fixing POS System shortcuts with AG logo...
echo.

REM Define custom AG logo path
set ICON_PATH="%~dp0ag_logo.ico"

REM Remove existing shortcuts
echo Removing existing shortcuts...
if exist "%USERPROFILE%\Desktop\POS System.lnk" del "%USERPROFILE%\Desktop\POS System.lnk"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\POS System\POS System.lnk" del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\POS System\POS System.lnk"

REM Create desktop shortcut
echo Creating desktop shortcut...
set SCRIPT="%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\POS System.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0POS System.exe" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "AG POS System" >> %SCRIPT%
echo oLink.IconLocation = %ICON_PATH% >> %SCRIPT%
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
echo oLink.Description = "AG POS System" >> %SCRIPT%
echo oLink.IconLocation = %ICON_PATH% >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo Shortcuts have been created with AG logo!
echo IMPORTANT: Make sure you have the ag_logo.ico file in the same folder as this script.
echo You should now be able to launch the POS System from the desktop shortcut or Start Menu.
echo.
pause 