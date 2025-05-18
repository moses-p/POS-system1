# POS System User Guide

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [User Roles](#user-roles)
4. [Basic Operations](#basic-operations)
5. [Inventory Management](#inventory-management)
6. [Sales Processing](#sales-processing)
7. [Reports](#reports)
8. [Offline Mode](#offline-mode)
9. [Mobile Access](#mobile-access)
10. [Troubleshooting](#troubleshooting)

## Installation

### Standard Installation
1. Copy the POS System folder to your computer
2. Run `Install.bat` to set up shortcuts and initialize the database
3. Use the desktop shortcut or Start Menu shortcut to launch the application

### Network Installation
To access the system from multiple devices:
1. Install on a server or main computer
2. Make sure the computer is accessible on your network
3. Other devices can access via the IP address in a web browser (e.g., http://192.168.1.x:5000)

## Getting Started

### First Login
- Default admin credentials:
  - Username: `admin`
  - Password: `admin123`
- **Important**: Change the default password immediately after first login

### Initial Setup
1. Add inventory items
2. Set up staff accounts
3. Configure system settings

## User Roles

### Admin
- Full access to all features
- Can manage users, inventory, and view all reports
- Access to system configuration

### Staff
- Process sales and orders
- Limited inventory management
- View their own sales reports

### Customer
- Regular users who can place orders online
- View their order history

## Basic Operations

### Navigation
- Dashboard: Overview of key metrics
- Products: Manage inventory
- Sales: Process transactions
- Reports: View business performance
- Users: Manage staff accounts (Admin only)

### Common Tasks
- Processing a sale
- Adding/editing inventory
- Viewing reports
- Managing users

## Inventory Management

### Adding Products
1. Go to Products > Add New
2. Enter product details
3. Set price, stock levels, and reorder points
4. Save the product

### Stock Management
- Restock: Update inventory levels when new stock arrives
- Monitor low stock alerts
- View stock movement history

### Price Updates
- Update prices individually or in bulk
- Price history is maintained for reference

## Sales Processing

### In-store Sales
1. Go to Sales > New Sale
2. Scan barcode or search for products
3. Add items to cart
4. Enter customer details (optional)
5. Process payment
6. Print receipt

### Offline Mode
The system automatically switches to offline mode when internet connection is lost:
- Sales are stored locally
- Data is synchronized when connection is restored

## Reports

### Available Reports
- Daily/Weekly/Monthly/Yearly Sales
- Product Performance
- Staff Performance
- Inventory Status

### Generating Reports
1. Go to Reports
2. Select report type
3. Set date range
4. View or export results

## Offline Mode

### How It Works
- System detects when internet connection is unavailable
- Switches to local database
- Operations continue without interruption
- Data synchronizes when connection returns

### Best Practices
- Regularly check connection status
- Manually sync if needed
- Verify data after extended offline periods

## Mobile Access

### Accessing on Mobile Devices
1. Connect to the same network as the server
2. Open web browser on mobile device
3. Navigate to the server's IP address (e.g., http://192.168.1.x:5000)
4. Login with your credentials

### Mobile Features
- Responsive design works on any screen size
- Can be added to home screen for app-like experience
- Full functionality available on mobile devices

## Troubleshooting

### Common Issues

#### System Won't Start
- Verify Python is installed
- Check database file is not corrupted
- Run as administrator

#### Database Errors
- Run `Reset Database.bat` to reset (warning: this erases all data)
- Check permissions on the database file

#### Synchronization Issues
- Ensure both devices are on the same network
- Check firewall settings
- Manual sync may be required

### Getting Help
- Contact system administrator
- Email support: givenwholesalers1@gmail.com
- Phone: 0782 413668 