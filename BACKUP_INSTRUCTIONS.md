# POS System Database Backup Instructions

## Overview

The POS System includes an automated backup solution to protect your business data. This document explains how to set up, run, and manage database backups.

## Backup Files

Three files are provided for database backup management:

1. **backup_database.bat** - The main script that performs the actual backup
2. **schedule_backups.bat** - A utility to set up automated scheduled backups
3. **BACKUP_INSTRUCTIONS.md** - This documentation file

## Manual Backups

To perform a manual backup at any time:

1. Navigate to your POS System installation folder
2. Double-click on `backup_database.bat`
3. A command window will open and show the backup progress
4. The backup will be created in the `backups` subfolder

Each backup file is named with the date and time it was created (e.g., `pos_backup_20250502_1435.db`).

## Automated Backups

To set up automated daily and weekly backups:

1. Right-click on `schedule_backups.bat` and select "Run as administrator"
2. Follow the on-screen instructions
3. The script will create two scheduled tasks:
   - Daily backup at 11:00 PM
   - Weekly full backup on Sundays at 10:00 PM

You can verify the scheduled tasks in Windows Task Scheduler.

## Backup Retention

The backup system automatically manages storage space:

- Only the 10 most recent backup files are kept
- Older backups are automatically deleted
- A log of all backups is maintained in `backup_log.txt`

## Restoring from Backup

If you need to restore from a backup:

1. Stop the POS System if it's running
2. Navigate to the `backups` folder
3. Identify the backup file you want to restore
4. Copy the backup file to `instance\pos.db` (replacing the existing file)
5. Restart the POS System

## Best Practices

- Keep copies of important backups in an external location (cloud storage, external drive)
- Periodically test the restore process to ensure backups are working correctly
- After major data changes, run a manual backup
- Check `backup_log.txt` periodically to ensure backups are running successfully

## Troubleshooting

If backups are not working:

1. Ensure the POS System has write permissions to the `backups` folder
2. Check that the database file exists at `instance\pos.db`
3. Verify that the scheduled tasks are active in Windows Task Scheduler
4. Review `backup_log.txt` for any error messages

For persistent issues, please contact technical support:
- Email: arisegeniusug@gmail.com
- Phone: +256743232445 