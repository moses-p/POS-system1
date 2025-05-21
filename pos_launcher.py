# This is the recommended entry point for desktop packaging (Windows/Mac/Linux) using PyInstaller.
# It ensures the database is initialized and opens the app in the default browser.
import os
import sys
import webbrowser
import threading
import time
import logging
import socket
import psutil
import webview
from app import app, db, init_db, check_db_integrity
# Patch sys.stdout and sys.stderr if running in a frozen (PyInstaller) windowed app
if hasattr(sys, 'frozen'):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
try:
    # Try importing directly
    from app import app, init_db
except ImportError:
    # If direct import fails, ensure current directory is in path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import app, init_db
from check_and_init_db import run_checks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.FileHandler("pos_startup.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def open_browser():
    """Open the browser after a short delay to give the server time to start"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.info.get('connections', []):
                if conn.laddr.port == port:
                    logger.info(f"Killing process {proc.info['pid']} using port {port}")
                    proc.kill()
        except Exception:
            continue

def find_free_port(start_port=5000, max_tries=20):
    port = start_port
    for _ in range(max_tries):
        if not is_port_in_use(port):
            return port
        port += 1
    raise RuntimeError("No free port found in range.")

def run_flask():
    """Run the Flask application in a separate thread"""
    try:
        # Initialize database if needed
        with app.app_context():
            if not os.path.exists('instance/pos.db'):
                logger.info("Initializing database...")
                init_db()
            else:
                logger.info("Checking database integrity...")
                check_db_integrity()
        
        # Run Flask app
        app.run(host='127.0.0.1', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Error running Flask: {e}")
        sys.exit(1)

def wait_for_server(host='127.0.0.1', port=5000, timeout=30):
    """Wait for the Flask server to become available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                logger.info("Server is ready!")
                return True
        except Exception as e:
            logger.debug(f"Waiting for server... {e}")
        time.sleep(1)
    logger.error("Server failed to start within timeout period")
    return False

def main():
    """Main function to start the application"""
    try:
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Wait for server to be ready
        if not wait_for_server():
            logger.error("Failed to start server")
            sys.exit(1)

        # Create and start the window
        window = webview.create_window(
            'POS System',
            'http://127.0.0.1:5000',
            width=1200,
            height=800,
            resizable=True,
            min_size=(800, 600),
            text_select=True,
            confirm_close=True
        )
        
        # Start the GUI event loop
        webview.start(debug=False)
        
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 