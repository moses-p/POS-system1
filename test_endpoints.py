import requests

BASE_URL = 'http://127.0.0.1:5000'  # Change if running on a different host/port
LOGIN_ROUTE = '/login'
ADMIN_CREDENTIALS = {'username': 'admin', 'password': 'admin123'}

# List of endpoints to test: (route, method, expected_status, description)
ENDPOINTS = [
    ('/', 'GET', 200, 'Home page'),
    ('/debug', 'GET', 200, 'Debug info'),
    ('/register', 'GET', 200, 'Registration page'),
    ('/login', 'GET', 200, 'Login page'),
    ('/logout', 'GET', 302, 'Logout (should redirect)'),
    ('/profile', 'GET', 302, 'Profile (should redirect if not logged in)'),
    ('/admin', 'GET', 302, 'Admin dashboard (should redirect if not logged in)'),
    ('/cart', 'GET', 200, 'Cart page'),
    ('/checkout', 'GET', 200, 'Checkout page'),
    ('/reports', 'GET', 302, 'Reports (should redirect if not logged in)'),
    ('/api/sales/daily', 'GET', 302, 'Daily sales API (should redirect if not logged in)'),
    ('/manifest.json', 'GET', 200, 'Manifest for PWA'),
    ('/troubleshoot', 'GET', 200, 'Diagnostics'),
    ('/offline.html', 'GET', 200, 'Offline page'),
]

PROTECTED_ENDPOINTS = [
    ('/checkout', 'GET', 200, 'Checkout page (authenticated)'),
    ('/troubleshoot', 'GET', 200, 'Diagnostics (authenticated)'),
]

def test_endpoint(route, method='GET', expected_status=200, description=None, session=None):
    url = BASE_URL + route
    try:
        sess = session or requests
        resp = sess.request(method, url, allow_redirects=False)
        status = resp.status_code
        result = 'PASS' if status == expected_status else f'FAIL (got {status})'
        print(f"[{result}] {method} {route} - {description or ''}")
        return resp
    except Exception as e:
        print(f"[ERROR] {method} {route} - {e}")
        return None

def login_as_admin():
    sess = requests.Session()
    # Get login page to get cookies
    sess.get(BASE_URL + LOGIN_ROUTE)
    # Post login credentials
    resp = sess.post(BASE_URL + LOGIN_ROUTE, data=ADMIN_CREDENTIALS, allow_redirects=True)
    print(f"[LOGIN] Response status: {resp.status_code}")
    print(f"[LOGIN] Response text: {resp.text[:200]} ...")
    if resp.url.endswith('/admin') or resp.status_code == 200:
        print("[LOGIN] Admin login successful.")
        return sess
    else:
        print("[LOGIN FAIL] Could not log in as admin.")
        return None

def main():
    print("\n--- API Endpoint Smoke Test (Unauthenticated) ---\n")
    for route, method, expected_status, description in ENDPOINTS:
        test_endpoint(route, method, expected_status, description)

    print("\n--- Protected Endpoints (Authenticated as Admin) ---\n")
    admin_sess = login_as_admin()
    if not admin_sess:
        print("[ERROR] Skipping authenticated tests due to login failure.")
        return
    for route, method, expected_status, description in PROTECTED_ENDPOINTS:
        resp = test_endpoint(route, method, expected_status, description, session=admin_sess)
        if resp is not None:
            snippet = resp.text[:200].replace('\n', ' ').replace('\r', '')
            print(f"    Response snippet: {snippet} ...\n")

if __name__ == '__main__':
    main() 