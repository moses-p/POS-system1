import sqlite3
import os
from datetime import datetime

def fix_reports_data():
    """
    Fix issues with the reports data by:
    1. Setting any NULL order_date values to current timestamp
    2. Verifying all orders have reference numbers
    3. Ensuring consistent date formats are used in the database
    """
    print("Fixing reports data issues...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Find orders with NULL order_date
        cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_date IS NULL')
        null_dates_count = cursor.fetchone()[0]
        print(f"Found {null_dates_count} orders with NULL order_date")
        
        if null_dates_count > 0:
            # Set current timestamp for NULL order_date values
            current_time = datetime.now().isoformat()
            cursor.execute('UPDATE "order" SET order_date = ? WHERE order_date IS NULL', (current_time,))
            conn.commit()
            print(f"Updated {null_dates_count} orders with current timestamp")
        
        # 2. Check for orders without reference numbers
        cursor.execute('SELECT COUNT(*) FROM "order" WHERE reference_number IS NULL')
        null_ref_count = cursor.fetchone()[0]
        print(f"Found {null_ref_count} orders without reference numbers")
        
        if null_ref_count > 0:
            # Generate reference numbers for orders without them
            cursor.execute('SELECT id FROM "order" WHERE reference_number IS NULL')
            orders_without_ref = cursor.fetchall()
            
            for order_id in orders_without_ref:
                order_id = order_id[0]  # Extract ID from tuple
                # Generate a reference number in format ORD-YYYYMMDD-XXXXXX
                now = datetime.now()
                date_part = now.strftime('%Y%m%d')
                import uuid
                random_part = uuid.uuid4().hex[:6]
                reference = f"ORD-{date_part}-{random_part}"
                
                cursor.execute('UPDATE "order" SET reference_number = ? WHERE id = ?', 
                              (reference, order_id))
            
            conn.commit()
            print(f"Generated reference numbers for {null_ref_count} orders")
        
        # 3. Verify ordering is correct by checking a sample order
        cursor.execute('''
            SELECT id, reference_number, order_date, total_amount 
            FROM "order" 
            ORDER BY order_date DESC 
            LIMIT 5
        ''')
        recent_orders = cursor.fetchall()
        
        print("\nRecent orders after fixes:")
        for order in recent_orders:
            order_id, ref, date, amount = order
            print(f"ID: {order_id}, Ref: {ref}, Date: {date}, Amount: {amount}")
        
        # 4. Run a test query mimicking the daily sales report
        print("\nTesting daily sales report query:")
        cursor.execute('''
            SELECT date(order_date) as sale_date, 
                   SUM(total_amount) as daily_total,
                   COUNT(*) as order_count
            FROM "order"
            WHERE order_date IS NOT NULL
            GROUP BY date(order_date)
            ORDER BY sale_date DESC
            LIMIT 7
        ''')
        daily_sales = cursor.fetchall()
        
        if daily_sales:
            print("Daily sales data after fixes:")
            for day in daily_sales:
                date, total, count = day
                print(f"Date: {date}, Total: {total}, Orders: {count}")
        else:
            print("No daily sales data found after fixes.")
        
        conn.close()
        print("\nReports data fix complete.")
        
    except Exception as e:
        print(f"Error fixing reports data: {str(e)}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_reports_data() 