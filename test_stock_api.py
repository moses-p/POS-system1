import requests
import json
import time
import sys

def test_stock_api():
    """Test the stock status API directly"""
    print("Testing stock status API...")
    
    # Base URL - update this if needed
    base_url = "http://localhost:5000"
    
    # Test the API endpoint
    try:
        timestamp = int(time.time() * 1000)
        url = f"{base_url}/api/stock_status?_t={timestamp}"
        print(f"Requesting: {url}")
        
        response = requests.get(url, 
                              headers={
                                  'Cache-Control': 'no-cache, no-store, must-revalidate',
                                  'Pragma': 'no-cache',
                                  'Expires': '0'
                              })
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            if data.get('success'):
                print("\nAPI test successful!")
                return True
            else:
                print(f"\nAPI returned error: {data.get('error')}")
                return False
        else:
            print(f"\nAPI request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\nRequest error: {str(e)}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_stock_api()
    sys.exit(0 if success else 1) 