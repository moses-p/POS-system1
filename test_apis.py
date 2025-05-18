import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000'

def test_api_endpoint(endpoint, method='GET', data=None):
    """Test an API endpoint and print the results"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        
        print(f"\nTesting {method} {endpoint}")
        print(f"Status Code: {response.status_code}")
        try:
            print("Response:", json.dumps(response.json(), indent=2))
        except:
            print("Response:", response.text)
        return response
    except Exception as e:
        print(f"Error testing {endpoint}: {str(e)}")
        return None

def main():
    # Test login
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    response = test_api_endpoint('/api/login', 'POST', login_data)
    if not response or response.status_code != 200:
        print("Login failed. Cannot proceed with other tests.")
        return
    
    # Get token from login response
    token = response.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test product endpoints
    test_api_endpoint('/api/products')
    test_api_endpoint('/api/products/1')
    
    # Test sales endpoints
    test_api_endpoint('/api/sales')
    test_api_endpoint('/api/sales/1')
    
    # Test expense endpoints
    test_api_endpoint('/api/expenses')
    
    # Test reports
    test_api_endpoint('/api/reports/daily')
    test_api_endpoint('/api/reports/monthly')
    test_api_endpoint('/api/reports/yearly')
    
    # Test inventory
    test_api_endpoint('/api/inventory')
    test_api_endpoint('/api/inventory/1')

if __name__ == '__main__':
    main() 