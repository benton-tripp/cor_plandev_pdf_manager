#!/usr/bin/env python3
"""
Test monitor detection and dialog positioning
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.manage_output_dir import get_monitor_info, find_monitor_for_cursor, FolderSelector

def test_monitor_detection():
    """Test monitor detection functionality"""
    print("=== Monitor Detection Test ===")
    
    # Test monitor detection
    monitors = get_monitor_info()
    print(f"\nFound {len(monitors)} monitor(s):")
    for i, monitor in enumerate(monitors):
        print(f"  Monitor {i+1}: ({monitor['left']}, {monitor['top']}) to ({monitor['right']}, {monitor['bottom']}) - {monitor['width']}x{monitor['height']}")
    
    # Test cursor positions
    test_positions = [
        (100, 100),      # Primary monitor
        (2933, 295),     # Your actual cursor position
        (1920, 100),     # Edge between monitors
        (2500, 500),     # Second monitor
        (-100, 100),     # Left of primary (if arranged that way)
    ]
    
    print(f"\n=== Cursor Position Tests ===")
    for cursor_x, cursor_y in test_positions:
        print(f"\nTesting cursor position: ({cursor_x}, {cursor_y})")
        target_monitor = find_monitor_for_cursor(cursor_x, cursor_y, monitors)
        print(f"  Target monitor: ({target_monitor['left']}, {target_monitor['top']}) to ({target_monitor['right']}, {target_monitor['bottom']})")
        
        # Calculate where dialog would be positioned
        dialog_width = 400
        dialog_height = 300
        
        dialog_x = cursor_x - (dialog_width // 2)
        dialog_y = cursor_y - (dialog_height // 2)
        
        dialog_x = max(target_monitor['left'], 
                     min(dialog_x, target_monitor['right'] - dialog_width))
        dialog_y = max(target_monitor['top'], 
                     min(dialog_y, target_monitor['bottom'] - dialog_height))
        
        print(f"  Dialog would be positioned at: ({dialog_x}, {dialog_y})")

def test_folder_dialog():
    """Test the actual folder dialog"""
    print(f"\n=== Folder Dialog Test ===")
    folder_selector = FolderSelector()
    
    print("Testing with cursor position (2933, 295)...")
    result = folder_selector.select_folder(cursor_x=2933, cursor_y=295)
    print(f"Selected folder: {result}")

if __name__ == '__main__':
    test_monitor_detection()
    
    # Uncomment to test actual dialog
    # test_folder_dialog()