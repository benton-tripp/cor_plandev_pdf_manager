#!/usr/bin/env python3
"""
Utility functions and classes for managing output directories
"""

import tempfile
import os
from tkinter import filedialog
import tkinter as tk

# Conditionally import Windows-specific modules
try:
    if os.name == 'nt':  # Only import on Windows
        import ctypes
        from ctypes import wintypes
        CTYPES_AVAILABLE = True
    else:
        CTYPES_AVAILABLE = False
except ImportError:
    CTYPES_AVAILABLE = False


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


def get_monitor_info():
    """Get information about all monitors"""
    monitors = []
    
    # Try Windows API with ctypes for accurate monitor information
    if os.name == 'nt' and CTYPES_AVAILABLE:
        try:
            # Use ctypes to call EnumDisplayMonitors properly
            user32 = ctypes.windll.user32
            
            # Define the callback function type
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, 
                                               wintypes.HMONITOR, 
                                               wintypes.HDC, 
                                               ctypes.POINTER(wintypes.RECT), 
                                               wintypes.LPARAM)
            
            def enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                rect = lprcMonitor.contents
                monitors.append({
                    'left': rect.left,
                    'top': rect.top, 
                    'right': rect.right,
                    'bottom': rect.bottom,
                    'width': rect.right - rect.left,
                    'height': rect.bottom - rect.top
                })
                return True
            
            # Call EnumDisplayMonitors with proper ctypes
            user32.EnumDisplayMonitors(None, None, MonitorEnumProc(enum_proc), 0)
            print(f"Detected {len(monitors)} monitors using Windows API:")
            for i, monitor in enumerate(monitors):
                print(f"  Monitor {i+1}: {monitor['left']},{monitor['top']} to {monitor['right']},{monitor['bottom']} ({monitor['width']}x{monitor['height']})")
        except Exception as e:
            print(f"Error getting Windows monitor info: {e}")
            monitors = []
    
    # Fallback: use tkinter to get screen info, including virtual screen for multi-monitor
    if not monitors:
        try:
            root = tk.Tk()
            root.withdraw()
            
            # Get virtual screen dimensions (covers all monitors)
            virtual_width = root.winfo_vrootwidth()
            virtual_height = root.winfo_vrootheight()
            virtual_x = root.winfo_vrootx()
            virtual_y = root.winfo_vrooty()
            
            # Get primary screen dimensions
            primary_width = root.winfo_screenwidth()
            primary_height = root.winfo_screenheight()
            
            root.destroy()
            
            print(f"Virtual screen: {virtual_width}x{virtual_height} at ({virtual_x}, {virtual_y})")
            print(f"Primary screen: {primary_width}x{primary_height}")
            
            # If virtual screen is larger than primary, we likely have multiple monitors
            if virtual_width > primary_width or virtual_height > primary_height:
                # Create a monitor entry for the entire virtual screen area
                monitors = [{
                    'left': virtual_x,
                    'top': virtual_y,
                    'right': virtual_x + virtual_width,
                    'bottom': virtual_y + virtual_height,
                    'width': virtual_width,
                    'height': virtual_height
                }]
                print(f"Using virtual screen for multi-monitor setup: {virtual_width}x{virtual_height}")
            else:
                # Single monitor setup
                monitors = [{
                    'left': 0,
                    'top': 0,
                    'right': primary_width,
                    'bottom': primary_height,
                    'width': primary_width,
                    'height': primary_height
                }]
                print(f"Using single monitor info: {primary_width}x{primary_height}")
                
        except Exception as e:
            print(f"Error getting fallback monitor info: {e}")
            # Last resort fallback
            monitors = [{
                'left': 0,
                'top': 0,
                'right': 1920,
                'bottom': 1080,
                'width': 1920,
                'height': 1080
            }]
    
    return monitors


def find_monitor_for_cursor(cursor_x, cursor_y, monitors):
    """Find which monitor contains the given cursor position"""
    for i, monitor in enumerate(monitors):
        if (monitor['left'] <= cursor_x < monitor['right'] and 
            monitor['top'] <= cursor_y < monitor['bottom']):
            print(f"Cursor ({cursor_x}, {cursor_y}) is on monitor {i+1}")
            return monitor
    
    # If cursor is not on any monitor, find the closest one
    print(f"Cursor ({cursor_x}, {cursor_y}) is not on any monitor, finding closest...")
    closest_monitor = monitors[0]
    closest_distance = float('inf')
    
    for monitor in monitors:
        # Calculate distance to center of monitor
        center_x = (monitor['left'] + monitor['right']) // 2
        center_y = (monitor['top'] + monitor['bottom']) // 2
        distance = ((cursor_x - center_x) ** 2 + (cursor_y - center_y) ** 2) ** 0.5
        
        if distance < closest_distance:
            closest_distance = distance
            closest_monitor = monitor
    
    print(f"Using closest monitor: {closest_monitor['left']},{closest_monitor['top']} to {closest_monitor['right']},{closest_monitor['bottom']}")
    return closest_monitor


class FolderSelector:
    """API class for webview to interact with Python"""

    def __init__(self):
        self.initialdir = get_default_output_folder()
    
    def select_folder(self, cursor_x=None, cursor_y=None):
        """Open folder selection dialog on the screen containing the cursor position"""
        try:
            # Create a root window and hide it
            root = tk.Tk()
            root.withdraw()
            
            # Position the root window to help dialog appear on correct screen
            try:
                if cursor_x is not None and cursor_y is not None:
                    # Use cursor position to determine target screen
                    print(f"Using cursor position: ({cursor_x}, {cursor_y})")
                    
                    # Get all monitor information
                    monitors = get_monitor_info()
                    
                    # Find which monitor contains the cursor
                    target_monitor = find_monitor_for_cursor(cursor_x, cursor_y, monitors)
                    
                    # Calculate dialog position within the target monitor
                    # Center the dialog on the screen that contains the cursor
                    dialog_width = 400
                    dialog_height = 300
                    
                    # Calculate center of the target monitor
                    monitor_center_x = (target_monitor['left'] + target_monitor['right']) // 2
                    monitor_center_y = (target_monitor['top'] + target_monitor['bottom']) // 2
                    
                    # Position dialog so its bottom-right corner is at the monitor center
                    dialog_x = monitor_center_x - dialog_width
                    dialog_y = monitor_center_y - dialog_height
                    
                    # Ensure dialog stays within the target monitor bounds (safety check)
                    padding = 10
                    dialog_x = max(target_monitor['left'] + padding, 
                                 min(dialog_x, target_monitor['right'] - dialog_width - padding))
                    dialog_y = max(target_monitor['top'] + padding, 
                                 min(dialog_y, target_monitor['bottom'] - dialog_height - padding))
                    
                    root.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
                    print(f"Positioning dialog at: ({dialog_x}, {dialog_y}) with bottom-right at monitor center ({monitor_center_x}, {monitor_center_y}) within bounds ({target_monitor['left']},{target_monitor['top']}) to ({target_monitor['right']},{target_monitor['bottom']})")
                else:
                    # Fallback to center of primary screen if no cursor position provided
                    screen_width = root.winfo_screenwidth()
                    screen_height = root.winfo_screenheight()
                    
                    # Position root window at center of primary screen
                    x = (screen_width // 2) - 200
                    y = (screen_height // 2) - 150
                    root.geometry(f"400x300+{x}+{y}")
                    
                    print(f"Using fallback center position: ({x}, {y}) on {screen_width}x{screen_height} screen")
                
                # Update the root window to ensure geometry is applied
                root.update_idletasks()
                
            except Exception as e:
                print(f"Warning: Could not position dialog optimally: {e}")
                # Still try to show dialog with default positioning
            
            # Bring to front and make topmost
            try:
                root.attributes('-topmost', True)
                root.lift()
                root.focus_force()
            except Exception as e:
                print(f"Warning: Could not bring dialog to front: {e}")
            
            # Open folder dialog
            print("Opening folder selection dialog...")
            folder_path = filedialog.askdirectory(
                parent=root,
                title="Select Output Folder",
                initialdir=os.path.expanduser("~/Documents")
            )
            
            print(f"User selected folder: {folder_path}")
            
            # Clean up
            root.destroy()
            
            return folder_path if folder_path else None
        except Exception as e:
            print(f"Error selecting folder: {e}")
            # Make sure to destroy root even on error
            try:
                if 'root' in locals():
                    root.destroy()
            except:
                pass
            return None