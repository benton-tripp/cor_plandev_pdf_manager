#!/usr/bin/env python3
"""
Utility functions and classes for managing output directories
"""

import tempfile
import os
from tkinter import filedialog
import tkinter as tk

# Create default output folder in user's Documents
def get_default_output_folder():
    """Get default output folder - Documents/PDF_Manager_Output"""
    try:
        # Try to get Documents folder
        if os.name == 'nt':  # Windows
            documents = os.path.join(os.path.expanduser('~'), 'Documents')
        else:  # macOS/Linux
            documents = os.path.join(os.path.expanduser('~'), 'Documents')
        
        output_folder = os.path.join(documents, 'PDF_Manager_Output')
        os.makedirs(output_folder, exist_ok=True)
        return output_folder
    except:
        # Fallback to temp folder if Documents not accessible
        return tempfile.mkdtemp(prefix='pdf_management_')
    

class FolderSelector:
    """API class for webview to interact with Python"""

    def __init__(self):
        self.initialdir = get_default_output_folder()
    
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