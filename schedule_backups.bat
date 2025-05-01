@echo off
echo Setting up scheduled database backups for POS System
echo ==================================================

REM Get the current directory
set SCRIPT_DIR=%~dp0
set BACKUP_SCRIPT=%SCRIPT_DIR%backup_database.bat

REM Check if backup script exists
if not exist "%BACKUP_SCRIPT%" (
    echo ERROR: Backup script not found at %BACKUP_SCRIPT%
    echo Please make sure backup_database.bat is in the same directory as this script.
    goto :END
)

REM Create scheduled task for daily backups
echo Creating daily backup task...
schtasks /create /tn "POS System Daily Backup" /tr "%BACKUP_SCRIPT%" /sc DAILY /st 23:00 /ru SYSTEM /f

if %ERRORLEVEL% EQU 0 (
    echo Successfully scheduled daily backups at 11:00 PM.
) else (
    echo Failed to create scheduled task.
    echo You may need to run this script as administrator.
    goto :END
)

REM Create scheduled task for weekly full backups
echo Creating weekly backup task...
schtasks /create /tn "POS System Weekly Full Backup" /tr "%BACKUP_SCRIPT%" /sc WEEKLY /d SUN /st 22:00 /ru SYSTEM /f

if %ERRORLEVEL% EQU 0 (
    echo Successfully scheduled weekly backups on Sunday at 10:00 PM.
) else (
    echo Failed to create weekly scheduled task.
    goto :END
)

echo.
echo Backup schedule created successfully!
echo Daily backups: Every day at 11:00 PM
echo Weekly backups: Every Sunday at 10:00 PM
echo.
echo Backup files will be stored in the 'backups' folder.
echo The system will retain the 10 most recent backups.

:END
pause 