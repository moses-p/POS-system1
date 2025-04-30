import requests
import time

print("Testing connection to Flask server...")
time.sleep(2)  # Give the server time to start up

try:
    response = requests.get("http://localhost:5000", timeout=5)
    print(f"Status code: {response.status_code}")
    print("Server is running!")
except Exception as e:
    print(f"Error: {e}")
    print("Server might not be running or is experiencing issues.") 