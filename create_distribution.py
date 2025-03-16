#!/usr/bin/env python3
"""
Script to create a distribution package for DirSnap.
This will build the executable and package it with the installer scripts.
"""

import os
import sys
import subprocess
import shutil
import zipfile
from datetime import datetime

def main():
    print("Creating DirSnap distribution package...")
    
    # Build the executable first
    print("Building executable...")
    if os.path.exists("build_exe.py"):
        subprocess.check_call([sys.executable, "build_exe.py"])
    else:
        print("Error: build_exe.py not found!")
        return
    
    # Create dist directory if it doesn't exist
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    # Check if the executable was created
    exe_path = os.path.join("dist", "DirSnap.exe")
    if not os.path.exists(exe_path):
        print(f"Error: {exe_path} not found!")
        return
    
    # Create a distribution directory
    dist_dir = os.path.join("dist", "DirSnap_Distribution")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # Copy files to distribution directory
    print("Copying files to distribution package...")
    shutil.copy(exe_path, dist_dir)
    shutil.copy("installer.bat", dist_dir)
    shutil.copy("uninstaller.bat", dist_dir)
    shutil.copy("install_context_menu.bat", dist_dir)
    shutil.copy("uninstall_context_menu.bat", dist_dir)
    
    # Create a README file
    readme_path = os.path.join(dist_dir, "README.txt")
    with open(readme_path, "w") as f:
        f.write("DirSnap - Directory Structure Visualization Tool\n")
        f.write("==============================================\n\n")
        f.write("Installation:\n")
        f.write("1. Right-click on installer.bat and select 'Run as administrator'\n")
        f.write("2. Follow the prompts to install DirSnap\n\n")
        f.write("Usage:\n")
        f.write("- Double-click DirSnap.exe to run the application\n")
        f.write("- Right-click on any folder and select 'Open with DirSnap'\n\n")
        f.write("Uninstallation:\n")
        f.write("1. Right-click on uninstaller.bat and select 'Run as administrator'\n")
        f.write("2. Follow the prompts to uninstall DirSnap\n")
    
    # Create a zip file
    today = datetime.now().strftime("%Y%m%d")
    zip_path = os.path.join("dist", f"DirSnap_v1.0_{today}.zip")
    print(f"Creating zip file: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
    
    print("\nDistribution package created successfully!")
    print(f"Zip file: {zip_path}")
    print("\nYou can now distribute this zip file to users.")

if __name__ == "__main__":
    main() 