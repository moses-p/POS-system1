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

if __name__ == '__main__':
    try:
        logger.info("Starting POS system...")
        run_checks()

        port = 5000
        if is_port_in_use(port):
            logger.warning(f"Port {port} is in use. Attempting to kill old process...")
            kill_process_on_port(port)
            time.sleep(1)
            if is_port_in_use(port):
                logger.warning(f"Port {port} is still in use. Searching for a free port...")
                port = find_free_port(5000)

        def open_browser_dynamic():
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{port}')
        threading.Thread(target=open_browser_dynamic).start()
        logger.info(f"Starting Flask server on port {port}...")
        app.run(debug=False, threaded=True, port=port)
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        sys.exit(1) 