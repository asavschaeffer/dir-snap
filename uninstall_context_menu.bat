@echo off
echo Removing DirSnap from Windows context menu...

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

:: Remove registry entries
echo Removing registry entries...

:: Remove from Windows 11 main context menu
reg delete "HKEY_CURRENT_USER\Software\Classes\Directory\shell\DirSnap" /f
reg delete "HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\DirSnap" /f
reg delete "HKEY_CURRENT_USER\Software\Classes\Drive\shell\DirSnap" /f

:: Remove from legacy context menu
reg delete "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /f
reg delete "HKEY_CLASSES_ROOT\Directory\Background\shell\DirSnap" /f
reg delete "HKEY_CLASSES_ROOT\Drive\shell\DirSnap" /f

:: Refresh Windows Explorer
echo Refreshing Windows Explorer...
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo DirSnap has been removed from your context menu.
echo.
pause 