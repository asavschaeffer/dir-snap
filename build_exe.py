#!/usr/bin/env python3
"""
Build script for creating a standalone executable of DirSnap.
This creates a single .exe file that users can double-click to run.
"""

import os
import sys
import subprocess
import shutil

def main():
    print("Building DirSnap executable...")
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build the executable
    cmd = [
        "pyinstaller",
        "--name=DirSnap",
        "--onefile",
        "--windowed",
        "--icon=resources/icon.ico",
        "--add-data=resources;resources",
        "main.py"
    ]
    
    # Create resources directory if it doesn't exist
    if not os.path.exists("resources"):
        os.makedirs("resources")
    
    # Run PyInstaller
    subprocess.check_call(cmd)
    
    print("\nBuild complete!")
    print("Executable created at: dist/DirSnap.exe")
    print("\nYou can now distribute this file to users.")

if __name__ == "__main__":
    main() 