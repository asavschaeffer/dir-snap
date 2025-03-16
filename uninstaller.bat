@echo off
echo DirSnap Uninstaller
echo ==================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This uninstaller requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo This will uninstall DirSnap from your computer.
echo.
set /p CONFIRM="Are you sure you want to uninstall DirSnap? (Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

:: Remove from context menu
echo.
echo Removing from context menu...
call uninstall_context_menu.bat

:: Remove Start Menu shortcut
echo Removing Start Menu shortcut...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DirSnap.lnk" 2>nul

:: Get installation directory
set INSTALL_DIR=%~dp0

:: Go up one level to get the parent directory
cd /d "%INSTALL_DIR%"

echo.
echo Uninstallation complete!
echo DirSnap has been removed from your computer.
echo.
echo Note: The installation folder at %INSTALL_DIR% has not been deleted.
echo You may delete it manually if desired.
echo.
echo Press any key to exit...
pause > nul 