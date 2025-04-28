@echo off
echo Building POS System Installer...
python -m PyInstaller pos_app.spec --noconfirm
echo.
echo Build complete! The executable is in the "dist\POS System" folder.
echo You can copy this entire folder to install on other computers.
pause 