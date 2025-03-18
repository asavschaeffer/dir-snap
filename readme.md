# DirSnap

**DirSnap** is a lightweight tool that captures directory structures in three distinct formats, tailored for different use cases—whether you're sharing with AI assistants, humans, or creating visual diagrams. No coding required—just point, click, and export!

## For Users

### Installation

1. **Download**: Get the latest `DirSnap_v2.0_YYYYMMDD.zip` from [GitHub Releases](https://github.com/asavschaeffer/dirsnap/releases).
2. **Extract**: Unzip the file to a temporary location.
3. **Install**: Right-click `installer.bat` and select "Run as administrator".
4. **Follow Prompts**: Complete the guided installation process.

### Usage

Launch DirSnap in one of two ways:

1. **Standalone Mode**:
   - Open DirSnap from the Start Menu.
   - Click "Choose Root Folder" to select a directory.
   - Pick an output format: "LLM Output", "Human Output", or "Diagram Output".
   - Use the "Save to Downloads" (↓) or "Copy to Clipboard" (📋) buttons.

2. **Context Menu Mode**:
   - Right-click a folder in Windows Explorer.
   - Choose "Open with DirSnap".
   - Select your format and export as above.

#### Output Formats
- **LLM Output**: A compact, token-efficient format for AI assistants (e.g., `d|path/to/dir`, `f|path/to/file`).
- **Human Output**: A simple, readable tree with emojis (e.g., `📁 parent → 📄 child.txt`).
- **Diagram Output**: A visual Mermaid diagram, customizable via settings (e.g., depth, item limits).

#### Settings
- Click the ⚙️ button to tweak:
  - **Diagram Output**: Choose diagram type (e.g., mindmap, flowchart), depth (default: 3), items per directory (default: 5), and code block wrapping.
  - **Downloads**: Enable auto-copy of file path to clipboard after saving.

### Uninstallation

1. Go to the installation folder (default: `C:\Program Files\DirSnap`).
2. Right-click `uninstaller.bat`, select "Run as administrator", and follow the prompts.

## For Developers

### Project Structure
easy-dir-context/
├── main.py                    # Entry point
├── build_exe.py               # Builds executable
├── create_distribution.py     # Creates distribution package
├── installer.bat              # Installer script
├── uninstaller.bat            # Uninstaller script
├── install_context_menu.bat   # Adds context menu
├── uninstall_context_menu.bat # Removes context menu
├── resources/                 # App resources
├── src/                       # Source code
│   ├── init.py
│   ├── ui/                    # UI components
│   │   ├── init.py
│   │   ├── app.py             # Main app logic
│   │   └── tooltip.py         # (Removed in v2.0, replaced with labels)
│   └── utils/                 # Utilities
│       ├── init.py
│       ├── file_utils.py      # File operations
│       └── tree_generators.py # Output format generators


### Building the Distribution

1. Install PyInstaller: `pip install pyinstaller`.
2. Run: `python create_distribution.py`.
3. Find the package in the `dist` folder.

### Development

1. Clone the repo.
2. Edit the code.
3. Test with `python main.py`.
4. Build as above.

## Troubleshooting

- **Copy Fails**: Use "Save to Downloads" instead.
- **Context Menu Absent**: Re-run the installer or `install_context_menu.bat` as admin.
- **Diagram Too Long**: Adjust depth/items in settings (⚙️).
- **Errors**: File a GitHub Issue with a screenshot and details.
