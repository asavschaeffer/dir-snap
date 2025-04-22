# **DirSnap: Directory Snapshot & Scaffolder**

A simple Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.

## **Description**

This tool has two main functions:

1. **Snapshot (Directory \-\> Map):** Scans an existing directory on your filesystem and generates a text-based map representing its structure (folders and files), suitable for copying. Includes options for output format (Standard Indent, Tabs, Tree), ignoring specific files/directories, and optionally including file/folder emojis.
2. **Scaffold (Map \-\> Directory):** Parses an indented text map (in various common formats) and creates the corresponding nested directory structure and empty files within a user-selected base directory on the filesystem.

## **Current Status (v3.1 \- Core Functionality Complete)**

The core snapshot and scaffold features are complete and working reliably across multiple formats (Standard Indent, Tabs, Tree). Key Quality-of-Life features (interactive exclusion, config persistence, context menu handling) are implemented. The next steps focus on minor enhancements and distribution preparation.

## **Features Implemented**

- **Snapshot:**
  - Generates directory maps in multiple formats: Standard Indent (2-space), Tabs, or Tree.
  - Option to include leading emojis (📁/📄) in the map output.
  - Adds a trailing / to directory names in the map.
  - Includes built-in default ignore patterns (e.g., .git, node_modules, \_\_pycache\_\_).
  - Loads additional user-defined default ignores from configuration file (config.json).
  - Allows adding custom ignore patterns (comma-separated) per run via GUI.
  - Runs map generation in a background thread to keep UI responsive.
  - Displays an indeterminate progress bar during map generation.
  - Interactive map exclusion:
    - Clicking a line in the generated map toggles a visual strikethrough.
    - Clicking a directory also toggles its children (cascading).
    - Toggling adds/removes the item(s) from the Custom Ignores field for transparency and persistence.
  - Buttons to manually copy map or save it to a .txt file.
  - Copy to Clipboard respects exclusions from _both_ struck-through lines _and_ the Custom Ignores field.
  - Option to automatically copy the map (with exclusions) to the clipboard on generation or after clicking to exclude (preference saved in config).
  - Status feedback label.
  - Informational label showing key default ignores (includes user-defined defaults if configured).
- **Scaffold:**
  - Parses multiple map formats: Consistent Spaces (2 or 4), Tabs, Tree-like prefixes (Unicode/ASCII), Generic Indentation (fallback).
  - Auto-detects input format, with manual override via dropdown (preference saved in config).
  - Runs structure creation in a background thread to keep UI responsive.
  - Displays a determinate progress bar during structure creation.
  - Interactive map exclusion:
    - Clicking a line in the input map toggles a visual strikethrough.
    - Clicking a directory also toggles its children (cascading visual only).
  - Creates the directory structure and empty files within a selected base directory, skipping items corresponding to struck-through lines (including children).
  - Allows pasting map text from clipboard or loading from a .txt file.
  - Status feedback label with success/error/ready states.
  - "Open Output Folder" button appears on success to open the created directory (cross-platform).
- **GUI:**
  - Simple tkinter/ttk interface with "Snapshot" and "Scaffold" tabs.
  - File/Directory browser integration.
  - Clear buttons ('X') for main input fields, styled to appear integrated.
  - "Clear Map" button for scaffold input.
  - Tooltips for key controls.
  - Status bars use color coding (Red/Green/Default).
  - Progress bars provide visual feedback for long operations.
  - Standard Menu Bar (File \-\> Exit, Edit \-\> Preferences..., Help \-\> View README/About).
- **Configuration:**
  - Settings (last used paths, format preferences, auto-copy state, user default ignores) are saved to config.json in the user's standard configuration directory on exit.
  - Settings are loaded on application startup.
  - Configuration file can be opened via "Edit \-\> Preferences..." menu.
- **Context Handling:**
  - Can be launched with a directory path (starts Snapshot mode).
  - Can be launched with a file path (starts Scaffold mode, loads file).
  - Can be launched targeting a base directory for scaffolding ("Create Here" workflow \- requires context menu setup).

## **Requirements**

- Python 3.x (developed on 3.x, likely compatible with 3.7+)
- tkinter / ttk (usually included with Python standard library)
- pyperclip (for clipboard access)

## **How to Run (from Source)**

1. Clone the repository:  
   git clone https://github.com/asavschaeffer/dir-snap  
   cd DirSnap \# Or your project folder name
2. (Optional but recommended) Create and activate a virtual environment:  
   python \-m venv venv  
   \# Windows  
   .\\venv\\Scripts\\activate  
   \# macOS/Linux  
   source venv/bin/activate
3. Install dependencies:  
   pip install \-r requirements.txt
4. Run the application:  
   python main.py
   - You can also test the core logic directly (without GUI) using the test harness within logic.py: python \-m DirSnap.logic

## **Development Plan / To-Do List**

- **Completed / Mostly Done:**
  - \~\~Core MVP Logic (Snapshot multiple formats, Scaffold multiple formats).\~\~
  - \~\~GUI Structure & Basic Functionality.\~\~
  - \~\~Context Handling (Launch Arguments).\~\~
  - \~\~QoL: Status Bars \+ Colors.\~\~
  - \~\~QoL: Default Ignores Label.\~\~
  - \~\~QoL: Clear Buttons (Styled).\~\~
  - \~\~QoL: Open Output Folder Button.\~\~
  - \~\~QoL: Tooltips.\~\~
  - \~\~Scaffold Parsers: Spaces(2/4), Tabs, Tree, Generic Fallback (Implemented & Fixed).\~\~
  - \~\~Multi-format Scaffold Parsing Structure (Orchestrator, Detector, Helpers).\~\~
  - \~\~Interactive exclusion (strikethrough) for Snapshot & Scaffold.\~\~
  - \~\~Cascading exclusion logic (visual & functional).\~\~
  - \~\~Background threading for Snapshot & Scaffold operations.\~\~
  - \~\~Progress bars (indeterminate & determinate) for background tasks.\~\~
  - \~\~Significant code refactoring.\~\~
  - \~\~Configuration File: Saving/loading settings (ignores, paths, prefs) to persistent file.\~\~
  - \~\~Help Menu: Basic About dialog and link to README.\~\~
- **Up Next (High Priority):**
  - **Config Persistence for Snapshot Options:** Save/Load the selected Snapshot Output Format and Emoji preference in config.json.
- **Essential for Deployment:**
  - **Distribution Prep (Packaging, Installer, Right-Click Setup):** Package using PyInstaller \--onedir, create an installer (e.g., Inno Setup), finalize and test right-click setup scripts/instructions.
- **Polish (Low Priority):**
  - **Further UI/UX Refinements:** Minor layout/theme adjustments, improved error dialogs.
  - Refine "Open Folder" logic (error handling, platform edge cases).
  - Refine Documentation (README, Technical Docs).
- **Future / Deferred Ideas:**
  - Browser Extension Integration.
  - Drag and Drop support for files/folders onto the UI.
  - Advanced Config (Sounds, UI Themes, In-App Settings Editor, Customizable Emojis).

## **License**

(Optional: Add your license here, e.g., MIT License)
