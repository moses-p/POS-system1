@echo off
echo Checking POS System shortcut issue...
echo.

REM Check if executable exists
if exist "dist\POS System\POS System.exe" (
    echo The POS System executable exists. Let's fix the shortcut.
    
    REM Run the shortcut fix script
    call Fix_Shortcuts.bat
    
    echo.
    echo Shortcuts have been fixed. The POS System should now launch properly.
    echo If the issue persists, please try running Fix_Shortcuts_with_Icon.bat.
) else (
    echo ERROR: The POS System executable is missing.
    echo.
    echo This is likely because the build process didn't complete successfully.
    echo.
    echo To fix this issue:
    echo 1. Make sure you have PyInstaller installed (pip install pyinstaller)
    echo 2. Run the build_standalone.bat script to create the executable
    echo 3. After the build completes, run Fix_Shortcuts.bat to create proper shortcuts
    echo.
    echo Would you like to run the build script now?
    choice /C YN /M "Run build_standalone.bat now"
    
    if errorlevel 2 goto :END
    if errorlevel 1 goto :RUNBUILD
)

goto :END

:RUNBUILD
echo.
echo Running build script...
call build_standalone.bat
echo.
echo Build completed. Now fixing shortcuts...
call Fix_Shortcuts.bat
echo.
echo Process completed. The POS System should now launch properly.

:END
pause 