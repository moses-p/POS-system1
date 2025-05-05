import sqlite3
import os
from datetime import datetime, timedelta

def verify_report_data():
    """
    Verify report data through direct SQL queries to match the API calls
    and confirm the data is consistent.
    """
    print("Verifying report data...")
    db_path = 'instance/pos.db'
    
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get today's date and calculate ranges
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        week_ago = today - timedelta(days=7)
        current_month_start = datetime(today.year, today.month, 1).date()
        current_year_start = datetime(today.year, 1, 1).date()
        
        # Print date ranges for verification
        print(f"Today: {today}")
        print(f"30 days ago: {thirty_days_ago}")
        print(f"Week ago: {week_ago}")
        print(f"Current month start: {current_month_start}")
        print(f"Current year start: {current_year_start}")
        
        # Check daily sales (last 30 days)
        print("\n1. Daily Sales (Last 30 days):")
        cursor.execute('''
            SELECT date(order_date) as sale_date, 
                   SUM(total_amount) as daily_total,
                   COUNT(*) as order_count
            FROM "order"
            WHERE order_date IS NOT NULL
            AND date(order_date) BETWEEN ? AND ?
            GROUP BY date(order_date)
            ORDER BY sale_date
        ''', (thirty_days_ago.isoformat(), today.isoformat()))
        daily_sales = cursor.fetchall()
        
        if daily_sales:
            total_amount = 0
            for day in daily_sales:
                print(f"Date: {day['sale_date']}, Total: {day['daily_total']}, Orders: {day['order_count']}")
                total_amount += day['daily_total']
            print(f"Total amount for last 30 days: {total_amount}")
        else:
            print("No daily sales data found.")
        
        # Check weekly sales 
        print("\n2. Weekly Sales (Recent weeks):")
        
        # We'll manually group by week for better clarity
        weeks = []
        current_date = thirty_days_ago
        while current_date <= today:
            week_end = current_date + timedelta(days=6)
            if week_end > today:
                week_end = today
                
            cursor.execute('''
                SELECT SUM(total_amount) as weekly_total,
                       COUNT(*) as order_count
                FROM "order"
                WHERE order_date IS NOT NULL
                AND date(order_date) BETWEEN ? AND ?
            ''', (current_date.isoformat(), week_end.isoformat()))
            
            result = cursor.fetchone()
            week_label = f"{current_date} to {week_end}"
            weekly_total = result['weekly_total'] if result['weekly_total'] else 0
            
            print(f"Week: {week_label}, Total: {weekly_total}, Orders: {result['order_count']}")
            weeks.append((week_label, weekly_total, result['order_count']))
            
            current_date += timedelta(days=7)
        
        # Check monthly sales
        print("\n3. Monthly Sales (Recent months):")
        
        # Get the last 12 months
        current_month = today.month
        current_year = today.year
        
        for i in range(3):  # Just show the last 3 months for brevity
            # Calculate month boundaries
            if current_month - i <= 0:
                month = 12 + (current_month - i)
                year = current_year - 1
            else:
                month = current_month - i
                year = current_year
                
            month_start = datetime(year, month, 1).date()
            
            # Calculate next month
            if month == 12:
                next_month_start = datetime(year + 1, 1, 1).date()
            else:
                next_month_start = datetime(year, month + 1, 1).date()
            
            cursor.execute('''
                SELECT SUM(total_amount) as monthly_total,
                       COUNT(*) as order_count
                FROM "order"
                WHERE order_date IS NOT NULL
                AND date(order_date) >= ?
                AND date(order_date) < ?
            ''', (month_start.isoformat(), next_month_start.isoformat()))
            
            result = cursor.fetchone()
            month_label = month_start.strftime('%B %Y')
            monthly_total = result['monthly_total'] if result['monthly_total'] else 0
            
            print(f"Month: {month_label}, Total: {monthly_total}, Orders: {result['order_count']}")
        
        # Check yearly sales
        print("\n4. Yearly Sales:")
        cursor.execute('''
            SELECT strftime('%Y', order_date) as year,
                   SUM(total_amount) as yearly_total,
                   COUNT(*) as order_count
            FROM "order"
            WHERE order_date IS NOT NULL
            GROUP BY strftime('%Y', order_date)
            ORDER BY year
        ''')
        
        yearly_sales = cursor.fetchall()
        if yearly_sales:
            for year in yearly_sales:
                print(f"Year: {year['year']}, Total: {year['yearly_total']}, Orders: {year['order_count']}")
        else:
            print("No yearly sales data found.")
        
        conn.close()
        print("\nReport data verification complete.")
        
    except Exception as e:
        print(f"Error verifying report data: {str(e)}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verify_report_data() 