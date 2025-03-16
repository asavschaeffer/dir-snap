@echo off
echo DirSnap Installer
echo ================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This installer requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo Welcome to the DirSnap installer!
echo.
echo This will install DirSnap on your computer and add it to your context menu.
echo.
set /p INSTALL_DIR="Where would you like to install DirSnap? [C:\Program Files\DirSnap]: "

if "%INSTALL_DIR%"=="" set INSTALL_DIR=C:\Program Files\DirSnap

:: Create installation directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy files
echo.
echo Copying files to %INSTALL_DIR%...
copy /Y "DirSnap.exe" "%INSTALL_DIR%\"
copy /Y "install_context_menu.bat" "%INSTALL_DIR%\"
copy /Y "uninstall_context_menu.bat" "%INSTALL_DIR%\"

:: Create Start Menu shortcut
echo Creating Start Menu shortcut...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\DirSnap.lnk');$s.TargetPath='%INSTALL_DIR%\DirSnap.exe';$s.Save()"

:: Add to context menu
echo Adding to context menu...
cd /d "%INSTALL_DIR%"
call install_context_menu.bat

echo.
echo Installation complete!
echo DirSnap has been installed to %INSTALL_DIR%
echo You can now right-click on any folder and select "Open with DirSnap".
echo.
echo Press any key to exit...
pause > nul 