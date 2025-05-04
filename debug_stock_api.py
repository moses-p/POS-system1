import requests
import json
import time

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
            try:
                data = response.json()
                print(f"Response Data: {json.dumps(data, indent=2)}")
                
                # Check for success flag
                if data.get('success'):
                    print("API call successful!")
                    products = data.get('products', {})
                    print(f"Number of products: {len(products)}")
                    
                    if len(products) > 0:
                        print("\nExample of first product stock info:")
                        product_id = list(products.keys())[0]
                        print(f"Product ID: {product_id}")
                        print(f"Stock: {products[product_id]['stock']}")
                        print(f"Name: {products[product_id]['name']}")
                else:
                    print(f"API call failed: {data.get('error', 'No error message')}")
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
                print(f"Raw response: {response.text[:200]}...")
        else:
            print(f"Failed with status code: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_stock_api() 