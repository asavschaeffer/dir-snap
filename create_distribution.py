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
    
    # Create a files subfolder for non-essential files
    files_dir = os.path.join(dist_dir, "files")
    os.makedirs(files_dir)
    
    # Copy files to distribution directory
    print("Copying files to distribution package...")
    shutil.copy(exe_path, files_dir)
    shutil.copy("install_context_menu.bat", files_dir)
    shutil.copy("uninstall_context_menu.bat", files_dir)
    
    # Create modified installer and uninstaller that reference the files subfolder
    create_modified_installer(dist_dir, files_dir)
    create_modified_uninstaller(dist_dir, files_dir)
    
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
        f.write("1. Navigate to your DirSnap installation folder (default: C:\\Program Files\\DirSnap)\n")
        f.write("2. Right-click on uninstaller.bat and select 'Run as administrator'\n")
        f.write("3. Follow the prompts to uninstall DirSnap\n\n")
        f.write("Troubleshooting:\n")
        f.write("- If the context menu entry doesn't appear, try reinstalling or manually running install_context_menu.bat as administrator\n")
        f.write("- Make sure you're running the installer as administrator\n")
    
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

def create_modified_installer(dist_dir, files_dir):
    """Create a modified installer.bat that references files in the subfolder."""
    installer_path = os.path.join(dist_dir, "installer.bat")
    with open(installer_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo DirSnap Installer\n")
        f.write("echo ================\n")
        f.write("echo.\n\n")
        
        f.write(":: Check if running as administrator\n")
        f.write("net session >nul 2>&1\n")
        f.write("if %errorLevel% neq 0 (\n")
        f.write("    echo This installer requires administrator privileges.\n")
        f.write("    echo Please right-click and select \"Run as administrator\".\n")
        f.write("    pause\n")
        f.write("    exit /b 1\n")
        f.write(")\n\n")
        
        f.write("echo Welcome to the DirSnap installer!\n")
        f.write("echo.\n")
        f.write("echo This will install DirSnap on your computer and add it to your context menu.\n")
        f.write("echo.\n")
        f.write("set /p INSTALL_DIR=\"Where would you like to install DirSnap? [C:\\Program Files\\DirSnap]: \"\n\n")
        
        f.write("if \"%INSTALL_DIR%\"==\"\" set INSTALL_DIR=C:\\Program Files\\DirSnap\n\n")
        
        f.write(":: Create installation directory\n")
        f.write("if not exist \"%INSTALL_DIR%\" mkdir \"%INSTALL_DIR%\"\n\n")
        
        f.write(":: Copy files\n")
        f.write("echo.\n")
        f.write("echo Copying files to %INSTALL_DIR%...\n")
        f.write("copy /Y \"%~dp0files\\DirSnap.exe\" \"%INSTALL_DIR%\\\"\n")
        f.write("copy /Y \"%~dp0files\\install_context_menu.bat\" \"%INSTALL_DIR%\\\"\n")
        f.write("copy /Y \"%~dp0files\\uninstall_context_menu.bat\" \"%INSTALL_DIR%\\\"\n")
        f.write("copy /Y \"%~dp0uninstaller.bat\" \"%INSTALL_DIR%\\\"\n\n")
        
        f.write(":: Create Start Menu shortcut\n")
        f.write("echo Creating Start Menu shortcut...\n")
        f.write("powershell \"$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DirSnap.lnk');$s.TargetPath='%INSTALL_DIR%\\DirSnap.exe';$s.Save()\"\n\n")
        
        f.write(":: Add to context menu\n")
        f.write("echo Adding to context menu...\n")
        f.write("cd /d \"%INSTALL_DIR%\"\n")
        f.write("call install_context_menu.bat\n\n")
        
        f.write("echo.\n")
        f.write("echo Installation complete!\n")
        f.write("echo DirSnap has been installed to %INSTALL_DIR%\n")
        f.write("echo You can now right-click on any folder and select \"Open with DirSnap\".\n")
        f.write("echo.\n")
        f.write("echo Press any key to exit...\n")
        f.write("pause > nul\n")

def create_modified_uninstaller(dist_dir, files_dir):
    """Create a modified uninstaller.bat for the distribution package."""
    uninstaller_path = os.path.join(dist_dir, "uninstaller.bat")
    with open(uninstaller_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo DirSnap Uninstaller\n")
        f.write("echo ==================\n")
        f.write("echo.\n\n")
        
        f.write(":: Check if running as administrator\n")
        f.write("net session >nul 2>&1\n")
        f.write("if %errorLevel% neq 0 (\n")
        f.write("    echo This uninstaller requires administrator privileges.\n")
        f.write("    echo Please right-click and select \"Run as administrator\".\n")
        f.write("    pause\n")
        f.write("    exit /b 1\n")
        f.write(")\n\n")
        
        f.write("echo This will uninstall DirSnap from your computer.\n")
        f.write("echo.\n")
        f.write("set /p CONFIRM=\"Are you sure you want to uninstall DirSnap? (Y/N): \"\n\n")
        
        f.write("if /i not \"%CONFIRM%\"==\"Y\" (\n")
        f.write("    echo Uninstallation cancelled.\n")
        f.write("    pause\n")
        f.write("    exit /b 0\n")
        f.write(")\n\n")
        
        f.write(":: Remove from context menu\n")
        f.write("echo.\n")
        f.write("echo Removing from context menu...\n")
        f.write("call uninstall_context_menu.bat\n\n")
        
        f.write(":: Remove Start Menu shortcut\n")
        f.write("echo Removing Start Menu shortcut...\n")
        f.write("del \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DirSnap.lnk\" 2>nul\n\n")
        
        f.write(":: Get installation directory\n")
        f.write("set INSTALL_DIR=%~dp0\n\n")
        
        f.write("echo.\n")
        f.write("echo Uninstallation complete!\n")
        f.write("echo DirSnap has been removed from your computer.\n")
        f.write("echo.\n")
        f.write("echo Note: The installation folder at %INSTALL_DIR% has not been deleted.\n")
        f.write("echo You may delete it manually if desired.\n")
        f.write("echo.\n")
        f.write("echo Press any key to exit...\n")
        f.write("pause > nul\n")

if __name__ == "__main__":
    main() 