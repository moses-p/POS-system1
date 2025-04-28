import os
import sys
import webbrowser
import threading
import time
from app import app, init_db

def open_browser():
    """Open the browser after a short delay to give the server time to start"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Start browser thread
    threading.Thread(target=open_browser).start()
    
    # Start the Flask app
    app.run(debug=False, threaded=True) 