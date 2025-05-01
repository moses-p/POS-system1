@echo off
echo POS System Database Backup
echo =======================

REM Set variables
set BACKUP_DIR=backups
set DB_FILE=instance\pos.db
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\pos_backup_%TIMESTAMP%.db

REM Create backup directory if it doesn't exist
if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%

REM Check if database file exists
if not exist %DB_FILE% (
    echo ERROR: Database file %DB_FILE% not found!
    goto :END
)

REM Create database backup
echo Creating backup of %DB_FILE%...
copy %DB_FILE% %BACKUP_FILE% > nul

REM Verify backup was created
if exist %BACKUP_FILE% (
    echo Backup created successfully: %BACKUP_FILE%
) else (
    echo ERROR: Backup failed!
    goto :END
)

REM Cleanup old backups (keep last 10)
echo Cleaning up old backups...
set COUNT=0
for /f "tokens=*" %%F in ('dir /b /o-d %BACKUP_DIR%\pos_backup_*.db') do (
    set /a COUNT+=1
    if !COUNT! GTR 10 (
        del %BACKUP_DIR%\%%F
        echo Deleted old backup: %%F
    )
)

REM Create log entry
echo %date% %time% - Backup created: %BACKUP_FILE% >> backup_log.txt

:END
echo.
echo Backup process completed.
echo. 