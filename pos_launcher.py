import os
import sys
import webbrowser
import threading
import time
import logging
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

if __name__ == '__main__':
    try:
        # Run database checks and initialization
        logger.info("Starting POS system...")
        run_checks()
        
        # Start browser thread
        threading.Thread(target=open_browser).start()
        
        # Start the Flask app
        logger.info("Starting Flask server...")
        app.run(debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        print(f"Error during startup: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1) 