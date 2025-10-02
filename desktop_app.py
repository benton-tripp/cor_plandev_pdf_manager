import webview
import threading
import time
import sys
import os
from app import app

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_flask():
    """Start Flask in a separate thread"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def create_window():
    """Create the desktop window"""
    # Start Flask in background
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Wait a moment for Flask to start
    time.sleep(2)
    
    # Create desktop window
    webview.create_window(
        'PlanDev PDF Manager',
        'http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600)
    )
    webview.start(debug=False)

if __name__ == '__main__':
    create_window()