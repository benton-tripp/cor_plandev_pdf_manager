import webview
import threading
import time
import sys
import os
import socket
from contextlib import closing
from tkinter import filedialog
import tkinter as tk
from app import app

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def find_free_port():
    """Find a free port to run Flask on"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

class Api:
    """API class for webview to interact with Python"""
    
    def select_folder(self):
        """Open folder selection dialog"""
        try:
            # Create a root window and hide it
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Open folder dialog
            folder_path = filedialog.askdirectory(
                title="Select Output Folder",
                initialdir=os.path.expanduser("~/Documents")
            )
            
            # Clean up
            root.destroy()
            
            return folder_path if folder_path else None
        except Exception as e:
            print(f"Error selecting folder: {e}")
            return None

def start_flask(port):
    """Start Flask in a separate thread"""
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False, threaded=True)

def create_window():
    """Create the desktop window"""
    # Find a free port
    port = find_free_port()
    
    # Start Flask in background
    flask_thread = threading.Thread(target=start_flask, args=(port,), daemon=True)
    flask_thread.start()
    
    # Wait a moment for Flask to start
    time.sleep(3)
    
    # Create API instance
    api = Api()
    
    # Create desktop window
    webview.create_window(
        'PlanDev PDF Manager',
        f'http://127.0.0.1:{port}',
        width=1300,
        height=1000,
        resizable=True,
        min_size=(600, 600),
        js_api=api
    )
    webview.start(debug=False)

if __name__ == '__main__':
    create_window()