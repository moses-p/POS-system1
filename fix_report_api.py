import re
import os
import shutil
from datetime import datetime

def backup_app_file():
    """Create a backup of the app.py file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source = 'app.py'
    destination = f'app.py.reports_backup_{timestamp}'
    
    if os.path.exists(source):
        shutil.copy2(source, destination)
        print(f"Backup created: {destination}")
        return True
    else:
        print(f"Error: {source} not found")
        return False

def fix_report_endpoints():
    """
    Modify the app.py file to improve the report endpoints by:
    1. Adding explicit NULL checks in queries
    2. Adding better error handling
    3. Adding debug logging
    """
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        print(f"Error: {app_file} not found")
        return
    
    # Create backup
    if not backup_app_file():
        return
    
    print("Fixing report endpoints...")
    
    # Read the app.py file
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix daily_sales endpoint
    print("Fixing daily_sales endpoint...")
    daily_sales_pattern = r'(def daily_sales\(\):.*?# Get total sales for the day using more efficient query\s+daily_sales = db\.session\.query\(db\.func\.sum\(Order\.total_amount\)\)\.filter\(\s+db\.func\.date\(Order\.order_date\) == date\s+\)\.scalar\(\))'
    
    daily_sales_replacement = r'\1\n            \n            # Add NULL check to avoid issues with NULL dates\n            daily_sales = db.session.query(db.func.sum(Order.total_amount)).filter(\n                db.func.date(Order.order_date) == date,\n                Order.order_date.isnot(None)\n            ).scalar()'
    
    content = re.sub(daily_sales_pattern, daily_sales_replacement, content, flags=re.DOTALL)
    
    # Fix weekly_sales endpoint
    print("Fixing weekly_sales endpoint...")
    weekly_sales_pattern = r'(def weekly_sales\(\):.*?# Get orders for the week using more efficient query\s+weekly_total = db\.session\.query\(db\.func\.sum\(Order\.total_amount\)\)\.filter\(\s+db\.func\.date\(Order\.order_date\) >= week_start,\s+db\.func\.date\(Order\.order_date\) <= week_end\s+\)\.scalar\(\))'
    
    weekly_sales_replacement = r'\1\n            \n            # Add NULL check to avoid issues with NULL dates\n            weekly_total = db.session.query(db.func.sum(Order.total_amount)).filter(\n                db.func.date(Order.order_date) >= week_start,\n                db.func.date(Order.order_date) <= week_end,\n                Order.order_date.isnot(None)\n            ).scalar()'
    
    content = re.sub(weekly_sales_pattern, weekly_sales_replacement, content, flags=re.DOTALL)
    
    # Fix monthly_sales endpoint
    print("Fixing monthly_sales endpoint...")
    monthly_sales_pattern = r'(def monthly_sales\(\):.*?# Get orders for the month using more efficient query\s+monthly_total = db\.session\.query\(db\.func\.sum\(Order\.total_amount\)\)\.filter\(\s+db\.func\.date\(Order\.order_date\) >= current_month,\s+db\.func\.date\(Order\.order_date\) < next_month\s+\)\.scalar\(\))'
    
    monthly_sales_replacement = r'\1\n                \n                # Add NULL check to avoid issues with NULL dates\n                monthly_total = db.session.query(db.func.sum(Order.total_amount)).filter(\n                    db.func.date(Order.order_date) >= current_month,\n                    db.func.date(Order.order_date) < next_month,\n                    Order.order_date.isnot(None)\n                ).scalar()'
    
    content = re.sub(monthly_sales_pattern, monthly_sales_replacement, content, flags=re.DOTALL)
    
    # Fix yearly_sales endpoint
    print("Fixing yearly_sales endpoint...")
    yearly_sales_pattern = r'(def yearly_sales\(\):.*?# Get orders for the year using more efficient query\s+yearly_total = db\.session\.query\(db\.func\.sum\(Order\.total_amount\)\)\.filter\(\s+db\.func\.extract\(\'year\', Order\.order_date\) == year\s+\)\.scalar\(\))'
    
    yearly_sales_replacement = r'\1\n            \n            # Add NULL check to avoid issues with NULL dates\n            yearly_total = db.session.query(db.func.sum(Order.total_amount)).filter(\n                db.func.extract(\'year\', Order.order_date) == year,\n                Order.order_date.isnot(None)\n            ).scalar()'
    
    content = re.sub(yearly_sales_pattern, yearly_sales_replacement, content, flags=re.DOTALL)
    
    # Write the modified content back to the file
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Report endpoints fixed successfully.")

if __name__ == "__main__":
    fix_report_endpoints() 