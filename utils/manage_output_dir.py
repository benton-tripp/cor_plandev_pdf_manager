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
        """Open folder selection dialog on the current screen"""
        try:
            # Create a root window and hide it
            root = tk.Tk()
            root.withdraw()
            
            # Position the root window to help dialog appear on correct screen
            try:
                # Try to get screen dimensions and position dialog appropriately
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                
                # Position root window at center of primary screen
                # This helps influence where the dialog appears
                x = (screen_width // 2) - 200
                y = (screen_height // 2) - 150
                root.geometry(f"400x300+{x}+{y}")
                
                # Update the root window to ensure geometry is applied
                root.update_idletasks()
                
            except Exception as e:
                print(f"Warning: Could not position dialog optimally: {e}")
            
            # Bring to front and make topmost
            root.attributes('-topmost', True)
            root.lift()
            root.focus_force()
            
            # Open folder dialog
            folder_path = filedialog.askdirectory(
                parent=root,
                title="Select Output Folder",
                initialdir=os.path.expanduser("~/Documents")
            )
            
            # Clean up
            root.destroy()
            
            return folder_path if folder_path else None
        except Exception as e:
            print(f"Error selecting folder: {e}")
            return None