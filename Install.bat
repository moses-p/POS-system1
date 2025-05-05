@echo off
echo Installing POS System...

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\POS System.lnk'); $Shortcut.TargetPath = '%~dp0POS System.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Save()"

REM Create Start Menu shortcut
echo Creating Start Menu shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('StartMenu') + '\POS System.lnk'); $Shortcut.TargetPath = '%~dp0POS System.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Save()"

REM Initialize database if needed
if not exist "instance\pos.db" (
    echo Initializing database...
    "POS System.exe" --init-db
)

echo Installation complete!
echo You can now launch the POS System from the desktop shortcut or Start Menu.
pause 