"""
Utility functions for handling filenames
"""
import os
import re
from pathlib import Path


def make_unique_filename(file_path):
    """
    Make a filename unique by appending (1), (2), etc. if the file exists.
    Uses Windows-style numbering.
    
    Args:
        file_path (str): The desired file path
    
    Returns:
        str: A unique file path that doesn't exist
    """
    if not os.path.exists(file_path):
        return file_path
    
    # Split the path into directory, name, and extension
    path_obj = Path(file_path)
    directory = path_obj.parent
    name = path_obj.stem
    extension = path_obj.suffix
    
    # Check if the filename already has a number in parentheses
    # Pattern matches: "filename (1)", "filename (2)", etc.
    pattern = r'^(.+?)\s*\((\d+)\)$'
    match = re.match(pattern, name)
    
    if match:
        # File already has a number, extract the base name and current number
        base_name = match.group(1).strip()
        current_number = int(match.group(2))
    else:
        # No number, use the full name as base
        base_name = name
        current_number = 0
    
    # Find the next available number
    counter = current_number + 1
    while True:
        if counter == 1 and current_number == 0:
            # First attempt: try "filename (1)"
            new_name = f"{base_name} (1)"
        else:
            # Subsequent attempts: "filename (2)", "filename (3)", etc.
            new_name = f"{base_name} ({counter})"
        
        new_path = directory / f"{new_name}{extension}"
        
        if not os.path.exists(new_path):
            return str(new_path)
        
        counter += 1
        
        # Safety check to prevent infinite loop
        if counter > 1000:
            raise ValueError(f"Unable to create unique filename after 1000 attempts for: {file_path}")


def make_unique_zip_filename(file_path):
    """
    Make a zip filename unique by appending (1), (2), etc. if the file exists.
    Specifically handles .zip extension.
    
    Args:
        file_path (str): The desired zip file path
    
    Returns:
        str: A unique zip file path that doesn't exist
    """
    # Ensure .zip extension
    if not file_path.lower().endswith('.zip'):
        file_path += '.zip'
    
    return make_unique_filename(file_path)