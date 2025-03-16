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
reg delete "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /f

echo.
echo DirSnap has been removed from your context menu.
echo.
pause 