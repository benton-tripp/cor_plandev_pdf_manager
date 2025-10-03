#!/usr/bin/env python3
"""
Utility functions for managing temporary directories
"""

import os
import shutil
import logging


def cleanup_temp_folder(temp_folder):
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder, ignore_errors=True)
        logging.debug(f"Cleaned up temporary folder: {temp_folder}")