#!/usr/bin/env python3
"""
DirSnap - A directory structure visualization tool

This tool helps you create snapshots of directory structures in various formats
that can be easily shared with AI assistants or other tools.
"""

import os
import sys

# Add the current directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the app class
from src.ui.app import DirSnapApp

if __name__ == "__main__":
    # Check if a directory path was provided as a command-line argument
    initial_directory = None
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            initial_directory = path
    
    # Start the application
    app = DirSnapApp(initial_directory)
    app.mainloop() 