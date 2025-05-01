@echo off
echo Fixing POS System shortcuts with better icon...
echo.

REM Download a proper POS icon if it doesn't exist
if not exist "%~dp0pos_icon.ico" (
    echo Downloading a proper POS system icon...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.iconarchive.com/download/i103366/paomedia/small-n-flat/shop.ico' -OutFile '%~dp0pos_icon.ico'}"
    
    if not exist "%~dp0pos_icon.ico" (
        echo Failed to download icon, will use default icon.
        set ICON_PATH="%~dp0static\favicon.ico"
    ) else (
        echo Icon downloaded successfully.
        set ICON_PATH="%~dp0pos_icon.ico"
    )
) else (
    echo Using existing POS icon.
    set ICON_PATH="%~dp0pos_icon.ico"
)

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
echo oLink.Description = "Point of Sale System" >> %SCRIPT%
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
echo oLink.Description = "Point of Sale System" >> %SCRIPT%
echo oLink.IconLocation = %ICON_PATH% >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo Shortcuts have been fixed with better icon!
echo You should now be able to launch the POS System from the desktop shortcut or Start Menu.
echo.
pause 