# AG POS System Installation Guide

This guide will help you install and set up the AG POS System on your server or local machine.

## System Requirements

- Python 3.8 or higher
- 2GB RAM minimum (4GB recommended)
- 1GB free disk space
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection for initial setup and updates

## Quick Installation (Windows)

1. Download the latest release from the releases page
2. Extract the ZIP file to your desired location
3. Run `setup.py` by double-clicking it or using the command:
   ```
   python setup.py
   ```
4. Follow the on-screen instructions
5. The system will automatically:
   - Create a virtual environment
   - Install all dependencies
   - Set up the database
   - Create initial admin and staff users

## Manual Installation

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd pos-system
```

### 2. Create and Activate Virtual Environment

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Linux/MacOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your configuration:
   - Set a strong `SECRET_KEY`
   - Configure database connection
   - Set up email settings
   - Update company information

### 5. Initialize Database

```bash
python init_db.py
```

### 6. Start the Application

Development mode:
```bash
python app.py
```

Production mode:
```bash
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

## Default Login Credentials

After installation, you can log in with these default credentials:

- Admin:
  - Username: admin
  - Password: admin123
- Staff:
  - Username: staff
  - Password: staff123

**Important:** Change these passwords immediately after first login!

## Production Deployment

### Using Nginx (Recommended)

1. Install Nginx:
   ```bash
   sudo apt-get install nginx
   ```

2. Configure Nginx:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. Set up as a system service:
   ```ini
   [Unit]
   Description=AG POS System
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/path/to/pos-system
   ExecStart=/path/to/pos-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

### Using Apache

1. Install Apache and mod_wsgi:
   ```bash
   sudo apt-get install apache2 libapache2-mod-wsgi-py3
   ```

2. Configure Apache:
   ```apache
   <VirtualHost *:80>
       ServerName your-domain.com
       WSGIDaemonProcess pos_system python-path=/path/to/pos-system/venv/lib/python3.8/site-packages
       WSGIProcessGroup pos_system
       WSGIScriptAlias / /path/to/pos-system/wsgi.py
   </VirtualHost>
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check database URL in `.env`
   - Ensure database server is running
   - Verify database credentials

2. **Email Not Working**
   - Check SMTP settings in `.env`
   - Verify email credentials
   - Check spam folder

3. **Static Files Not Loading**
   - Check file permissions
   - Verify static folder path
   - Clear browser cache

### Getting Help

If you encounter any issues:
1. Check the logs in `pos_system.log`
2. Review the documentation
3. Contact support at givenwholesalers1@gmail.com

## Security Recommendations

1. Always use HTTPS in production
2. Keep Python and all dependencies updated
3. Regularly backup your database
4. Use strong passwords
5. Enable two-factor authentication if available
6. Regularly review user access and permissions

## Backup and Restore

### Database Backup

```bash
# SQLite
sqlite3 pos.db .dump > backup.sql

# PostgreSQL
pg_dump pos_db > backup.sql
```

### Restore from Backup

```bash
# SQLite
sqlite3 pos.db < backup.sql

# PostgreSQL
psql pos_db < backup.sql
```

## Updates

To update the system:

1. Backup your database and `.env` file
2. Pull the latest changes:
   ```bash
   git pull origin main
   ```
3. Update dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   flask db upgrade
   ```
5. Restart the application

## Support

For support and questions:
- Email: givenwholesalers1@gmail.com
- Documentation: [User Guide](USER_GUIDE.md)
- GitHub Issues: [Report Issues](https://github.com/your-repo/issues)

© 2025 arisegenius. All Rights Reserved. 