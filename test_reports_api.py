import requests
import json
from datetime import datetime, timedelta
import sys

def test_api_endpoints():
    """Test the reports API endpoints by making direct requests."""
    
    # Base URL - update this to match your server address
    base_url = "http://localhost:5000"
    
    # Initialize session to maintain cookies
    session = requests.Session()
    
    # Login first to get session cookie
    print("Logging in...")
    try:
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        login_url = f"{base_url}/login"
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        if response.status_code != 302:  # Expecting a redirect after successful login
            print(f"Login failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return
    
    # Test endpoints
    endpoints = [
        ("/api/sales/daily", "Daily Sales"),
        ("/api/sales/weekly", "Weekly Sales"),
        ("/api/sales/monthly", "Monthly Sales"),
        ("/api/sales/yearly", "Yearly Sales")
    ]
    
    # Create date parameters for daily endpoint
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    daily_params = {
        "start_date": thirty_days_ago.strftime("%Y-%m-%d"),
        "end_date": today.strftime("%Y-%m-%d")
    }
    
    for endpoint, name in endpoints:
        print(f"\nTesting {name} endpoint: {endpoint}")
        try:
            # Add parameters for daily endpoint
            params = daily_params if "daily" in endpoint else {}
            
            response = session.get(f"{base_url}{endpoint}", params=params)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                pretty_json = json.dumps(data, indent=4)
                print(f"Response data:\n{pretty_json}")
                
                # Check for sales data
                if "sales" in data:
                    total_sales = sum(data["sales"])
                    print(f"Total sales: {total_sales}")
                    
                    # Check if we have any non-zero sales
                    if total_sales > 0:
                        print("✅ Has sales data")
                    else:
                        print("❌ No sales data found")
                else:
                    print("❌ No 'sales' key in response")
            else:
                print(f"❌ Failed request: {response.text}")
                
        except Exception as e:
            print(f"❌ Error testing {endpoint}: {str(e)}")
    
    print("\nAPI testing complete.")

if __name__ == "__main__":
    test_api_endpoints() 