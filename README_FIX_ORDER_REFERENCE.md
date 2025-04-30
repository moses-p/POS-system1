# Fix for Order Creation Issue

## Problem

There is an SQLite error when trying to create new orders:

```
Error creating order: (sqlite3.OperationalError) table order has no column named reference_number
[SQL: INSERT INTO "order" (reference_number, customer_id, order_date, total_amount, status, customer_name, customer_phone, customer_email, customer_address, order_type, created_by_id, updated_at, completed_at, viewed, viewed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)]
```

This is happening because there's a discrepancy between the SQLAlchemy model definition and the actual database schema.

## Root Cause

1. The database schema has been inconsistently updated.
2. The SQLAlchemy model includes a `reference_number` column, but the database table structure doesn't match.
3. Inspection of the database shows the column exists, but SQLite doesn't recognize it when inserting data.

## Fix Options

### Option 1: Use the Fix DB Schema Script (Recommended)

1. Run the `fix_db_schema.py` script to rebuild the order table with the correct schema.

```
python fix_db_schema.py
```

This script will:
- Check for and drop dependent views
- Create a new table with the correct schema 
- Copy existing order data
- Swap the tables
- Recreate indexes
- Generate reference numbers for any existing orders without them

### Option 2: Use Direct SQL Fallback

If Option 1 doesn't resolve the issue, you can implement a fallback mechanism by:

1. Copy the `create_order_direct.py` file to your project.
2. Update the `create_order` function in `app.py` using the code in `app_patched.py`.

This will:
- First try to create orders using SQLAlchemy
- If that fails, it will fall back to using direct SQL
- Successfully created orders will still be accessible through your application

## Testing

After implementing either solution, you can verify that order creation works by:

1. Running the `test_direct_order.py` script.
2. Testing the actual order creation in your application.

## Additional Notes

- The database schema fix won't affect existing data.
- If you have database migrations, make sure they're properly updated to include the `reference_number` column.
- For a long-term solution, consider implementing a database migration system if you haven't already.

## Troubleshooting

If you still encounter issues:

1. Check that the database user has write permissions to the database.
2. Make sure the application is restarted after making changes.
3. Try creating a simple test table and column to verify basic database operations work.
4. Check SQLAlchemy connection settings in your configuration. 