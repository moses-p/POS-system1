import requests
import sys
import time

def test_endpoints():
    base_url = "http://localhost:5000"
    
    # Try to connect multiple times in case the server is still starting
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt+1}/{max_attempts} to connect to {base_url}")
            response = requests.get(base_url)
            if response.status_code == 200:
                print(f"✅ Home page accessible! Status code: {response.status_code}")
                break
            else:
                print(f"❌ Home page returned status code: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed. Server might not be running yet.")
            if attempt < max_attempts - 1:
                print("Waiting 2 seconds before retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            break
    else:
        print("Failed to connect to the server after multiple attempts.")
        return False
    
    # Test a few more endpoints
    endpoints = [
        "/login",
        "/register",
        "/cart"
    ]
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url)
            if response.status_code in [200, 302]:  # 302 is redirect, often valid for login pages
                print(f"✅ {endpoint} accessible! Status code: {response.status_code}")
            else:
                print(f"❌ {endpoint} returned status code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error accessing {endpoint}: {str(e)}")
    
    return True

if __name__ == "__main__":
    print("Testing if the POS system is running...")
    result = test_endpoints()
    if result:
        print("\nBasic functionality test passed! The system appears to be working.")
    else:
        print("\nBasic functionality test failed. The system may not be working correctly.")
        sys.exit(1) 