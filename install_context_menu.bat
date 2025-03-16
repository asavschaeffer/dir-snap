@echo off
echo Adding DirSnap to Windows context menu...

:: Get the current directory where DirSnap.exe is located
set DIRSNAP_PATH=%~dp0DirSnap.exe

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

:: Add registry entries for folder context menu
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%1\"" /f

echo.
echo DirSnap has been added to your context menu!
echo You can now right-click on any folder and select "Open with DirSnap".
echo.
pause 