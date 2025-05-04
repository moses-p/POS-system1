# POS System

A comprehensive Point of Sale (POS) system built with Flask, featuring both online and offline functionality with Progressive Web App (PWA) capabilities.

## Features

### User Management
- Multi-level user authentication (Admin, Staff, Regular Users, Guests)
- Secure login/register with password hashing
- Role-based access control for different features
- User profile management

### Admin Dashboard
- Real-time sales analytics and reporting
- User management (create/manage staff and admin users)
- System-wide settings and configurations
- Sales reports (daily, weekly, monthly, yearly)

### Inventory Management
- Comprehensive product management
- Barcode scanning support
- Stock level monitoring with reorder points
- Price history tracking
- Unit and currency customization
- Batch restocking functionality

### Sales Processing
- Point of sale interface for staff
- Customer information management
- In-store and online sales processing
- Barcode scanning for quick checkout
- Receipt generation

### Shopping Cart & Checkout
- Real-time cart updates
- Guest checkout support
- Customer information storage
- Order history and tracking

### Offline Capability
- Full offline functionality via service worker
- Local storage of transactions
- Automatic synchronization when back online
- Offline-first design with PWA features

### Progressive Web App (PWA)
- Installable on mobile and desktop devices
- Works offline with cached resources
- Push notifications support
- Responsive design for all device sizes

### Mobile Optimization
- Touch-friendly interface
- Responsive layouts for all screen sizes
- Mobile-specific UI enhancements
- Gesture support for touch devices

## Technical Features
- RESTful API endpoints for all operations
- Service worker for offline caching
- IndexedDB for offline data storage
- Real-time data synchronization
- Secure authentication and data protection

## Installation

### Prerequisites
- Python 3.8+ installed
- pip (Python package manager)
- SQLite (development) or PostgreSQL (production)
- Modern web browser with JavaScript enabled

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd pos-system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (create a .env file with the following):
```
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///pos.db
FLASK_ENV=development
```

5. Initialize the database:
```bash
python init_db.py
```

6. Create initial admin and staff users:
```bash
python create_users.py
```

7. Run the development server:
```bash
python app.py
```

8. Access the application at http://localhost:5000

### Default Login Credentials
- Admin: 
  - Username: admin
  - Password: admin123
- Staff:
  - Username: staff
  - Password: staff123

## Production Deployment

### Server Requirements
- Linux server (recommended)
- Python 3.8+
- PostgreSQL database
- Nginx or Apache web server
- SSL certificate for HTTPS

### Deployment Steps

1. Set up production environment variables:
```
SECRET_KEY=<strong_random_string>
DATABASE_URL=postgresql://username:password@localhost/pos_db
FLASK_ENV=production
```

2. Configure your web server (Nginx example):
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. Run with a production WSGI server:
```bash
gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app
```

4. Set up as a service (systemd example):
```
[Unit]
Description=POS System
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/pos-system
ExecStart=/path/to/pos-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Mobile/Offline Usage

This system is designed as a Progressive Web App (PWA) and can be installed on mobile devices:

1. Open the website in a modern browser (Chrome, Safari, Edge)
2. Access the menu and select "Add to Home Screen" or "Install"
3. The app will now appear on your device home screen
4. The app will work offline using cached data
5. When offline:
   - You can view products and add to cart
   - Staff can process in-store sales
   - Data will be stored locally
   - When back online, data will automatically sync

## API Documentation

The system provides the following API endpoints:

- `/api/sales/daily` - Get daily sales data
- `/api/sales/weekly` - Get weekly sales data
- `/api/sales/monthly` - Get monthly sales data
- `/api/sales/yearly` - Get yearly sales data
- `/api/pending_orders` - Get pending orders
- `/api/sync_offline_order` - Sync offline orders
- `/get_cart_count` - Get current cart item count

All endpoints require authentication except `/get_cart_count`.

## Database Schema

The system uses the following main data models:

- User - Manages user accounts and roles
- Product - Stores product information
- StockMovement - Tracks inventory changes
- Order - Stores order information
- OrderItem - Individual items in an order
- Cart - Shopping cart for users
- CartItem - Items in shopping cart
- PriceChange - History of product price changes

## Security Features

- Password hashing using Werkzeug
- CSRF protection
- XSS protection headers
- Content security policy
- Input validation and sanitization
- Role-based access control
- Secure session management

## Troubleshooting

### Common Issues

1. **Database Migration Errors**
   - Run `python run_migration.py` to update database schema

2. **Login Issues**
   - Reset user passwords with `python create_users.py`
   - Clear browser cache and cookies

3. **Offline Sync Problems**
   - Check browser console for errors
   - Verify internet connection
   - Try clearing IndexedDB storage

4. **Service Worker Issues**
   - In Chrome, go to chrome://serviceworker-internals/
   - Unregister the service worker and reload

## License

This project is licensed under the MIT License.

## Acknowledgements

- Flask and extensions contributors
- Bootstrap for responsive UI components
- FontAwesome for icons
- All open source contributors

# POS System - Distribution Guide

## Desktop Packaging (Windows/Mac/Linux)

This POS system can be packaged as a standalone desktop application using PyInstaller. This allows you to run the app without needing to install Python or any dependencies.

### Build the Desktop App

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Build the executable:**
   ```sh
   pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" pos_launcher.py
   ```
   - On Mac/Linux, replace `;` with `:` in the `--add-data` arguments.

3. **Find the executable in the `dist/` directory.**
   - On Windows: `dist/pos_launcher.exe`
   - On Mac/Linux: `dist/pos_launcher`

4. **Run the executable:**
   - Double-click or run from terminal:
     ```sh
     ./dist/pos_launcher.exe  # Windows
     ./dist/pos_launcher      # Mac/Linux
     ```
   - The app will open in your default browser at [http://localhost:5000](http://localhost:5000)

---

## PWA / Mobile Installability

This POS system is a Progressive Web App (PWA). You can install it on your phone or tablet for a native app-like experience.

### How to Install on Mobile

1. **Access the app in your mobile browser** (Chrome, Edge, Safari, etc.).
2. **Look for the "Install" or "Add to Home Screen" prompt.**
   - If you don't see it, open the browser menu and select "Add to Home Screen".
3. **The app will be installed and appear on your home screen like a native app.**

### PWA Features
- Works offline (limited functionality)
- Installable on Android and iOS
- Responsive design for all screen sizes

---

## Notes
- For PWA features to work, the app must be served over `http://localhost` (for local use) or `https://` (for production).
- For desktop packaging, all static and template files are bundled automatically.

---

For more details, see the full documentation in `STOCK_SYSTEM_README.md`. 