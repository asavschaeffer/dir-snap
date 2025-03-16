# DirSnap

**DirSnap** is an easy-to-use tool that lists all files and folders in a directory you choose. No coding needed—just click and go!

## Download and Run

1. **Download**: Grab `DirSnap.exe` from [GitHub Releases](https://github.com/asavschaeffer/dirsnap/releases) (Windows) or the equivalent for macOS/Linux.
2. **Run**: Double-click the file to launch the app.
3. **Use**:
   - Click "Choose Root Folder" to select a directory.
   - Choose a format (Text List, JSON, or Mermaid).
   - Click the download button (↓) to save to Downloads or clipboard button (📋) to copy to clipboard.

No installation required—everything's bundled in!

## Requirements

- Windows, macOS, or Linux.
- No Python or command-line knowledge needed.

## For Developers

### Project Structure

The project now follows a modular architecture:

```
easy-dir-context/
├── main.py                 # Entry point
├── run.bat                 # Windows run script
├── run.sh                  # Unix/Linux/Mac run script
├── requirements.txt        # Dependencies (none required)
├── src/                    # Source code package
│   ├── __init__.py         # Package marker
│   ├── ui/                 # User interface components
│   │   ├── __init__.py     # Package marker
│   │   ├── app.py          # Main application class
│   │   └── tooltip.py      # Tooltip widget
│   └── utils/              # Utility functions
│       ├── __init__.py     # Package marker
│       ├── file_utils.py   # File-related utilities
│       └── tree_generators.py # Tree generation functions
```

### Running from Source

To run the application from source:

#### Windows

```
run.bat
```

or

```
python main.py
```

#### macOS/Linux

```
chmod +x run.sh
./run.sh
```

or

```
python3 main.py
```

### Development

1. Clone the repository
2. Make your changes
3. Run the application using one of the methods above

## Troubleshooting

- **Copy Doesn't Work**: Download a version with `pyperclip` included (check release notes).
- **Errors**: Contact me via GitHub Issues with a screenshot. To be honest you're probably better off just cloning and dumping it into grok lol
