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
echo Adding registry entries...

:: For Windows 11 main context menu (Shell Extensions)
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%1\"" /f

:: For directory background in Windows 11 main context menu
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%V\"" /f

:: For drives in Windows 11 main context menu
reg add "HKEY_CURRENT_USER\Software\Classes\Drive\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Drive\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CURRENT_USER\Software\Classes\Drive\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%1\"" /f

:: For legacy context menu (Show more options)
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CLASSES_ROOT\Directory\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%1\"" /f

reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%V\"" /f

reg add "HKEY_CLASSES_ROOT\Drive\shell\DirSnap" /ve /d "Open with DirSnap" /f
reg add "HKEY_CLASSES_ROOT\Drive\shell\DirSnap" /v "Icon" /d "\"%DIRSNAP_PATH%\"" /f
reg add "HKEY_CLASSES_ROOT\Drive\shell\DirSnap\command" /ve /d "\"%DIRSNAP_PATH%\" \"%%1\"" /f

:: Refresh Windows Explorer
echo Refreshing Windows Explorer...
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo DirSnap has been added to your context menu!
echo You can now right-click on any folder and select "Open with DirSnap".
echo.
pause 