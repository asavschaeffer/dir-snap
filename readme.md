# DirSnap

**DirSnap** is an easy-to-use tool that lists all files and folders in a directory you choose. No coding needed—just click and go!

## For Users

### Installation

1. **Download**: Download the latest `DirSnap_v1.0_YYYYMMDD.zip` from [GitHub Releases](https://github.com/asavschaeffer/dirsnap/releases)
2. **Extract**: Extract the zip file to a temporary location
3. **Install**: Right-click on `installer.bat` and select "Run as administrator"
4. **Follow prompts**: The installer will guide you through the installation process

### Usage

There are two ways to use DirSnap:

1. **Standalone Mode**:

   - Launch DirSnap from the Start Menu
   - Click "Choose Root Folder" to select a directory
   - Choose a format (Text List, JSON, or Mermaid)
   - Click the download button (↓) to save to Downloads or clipboard button (📋) to copy to clipboard

2. **Context Menu Mode**:
   - Right-click on any folder in Windows Explorer
   - Select "Open with DirSnap" from the context menu
   - The app will open with that folder already loaded
   - Choose a format and use the buttons as above

### Uninstallation

1. Navigate to the DirSnap installation folder (default: `C:\Program Files\DirSnap`)
2. Right-click on `uninstaller.bat` and select "Run as administrator"
3. Follow the prompts to uninstall DirSnap

## For Developers

### Project Structure

The project follows a modular architecture:

```
easy-dir-context/
├── main.py                    # Entry point
├── build_exe.py               # Script to build executable
├── create_distribution.py     # Script to create distribution package
├── installer.bat              # Windows installer
├── uninstaller.bat            # Windows uninstaller
├── install_context_menu.bat   # Script to add context menu entry
├── uninstall_context_menu.bat # Script to remove context menu entry
├── resources/                 # Application resources
├── src/                       # Source code package
│   ├── __init__.py            # Package marker
│   ├── ui/                    # User interface components
│   │   ├── __init__.py        # Package marker
│   │   ├── app.py             # Main application class
│   │   └── tooltip.py         # Tooltip widget
│   └── utils/                 # Utility functions
│       ├── __init__.py        # Package marker
│       ├── file_utils.py      # File-related utilities
│       └── tree_generators.py # Tree generation functions
```

### Building the Distribution Package

To create a distribution package:

1. Install PyInstaller: `pip install pyinstaller`
2. Run the distribution script: `python create_distribution.py`
3. The distribution package will be created in the `dist` folder

### Development

1. Clone the repository
2. Make your changes
3. Run the application using `python main.py`
4. Build the distribution package as described above

## Troubleshooting

- **Copy Doesn't Work**: Try using the "Save to Downloads" option instead
- **Context Menu Missing**: Run the installer again or manually run `install_context_menu.bat` as administrator
- **Errors**: Contact me via GitHub Issues with a screenshot
