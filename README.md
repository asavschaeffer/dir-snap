# **Directory Mapper & Scaffolder**

A simple Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.

## **Description**

This tool has two main functions:

1. **Snapshot (Directory \-\> Map):** Scans an existing directory on your filesystem and generates a text-based map representing its structure (folders and files), suitable for copying. Includes options for ignoring specific files/directories. (Currently outputs one format).
2. **Scaffold (Map \-\> Directory):** Parses an indented text map and creates the corresponding nested directory structure and empty files within a user-selected base directory on the filesystem. Includes support for multiple common map formats via auto-detection or manual selection.

## **Current Status (Functional MVP \+ QoL)**

The core functionality is complete and working. Several Quality-of-Life features have been added. The next steps involve adding persistence (config file), more snapshot flexibility, and preparing for distribution (packaging/installer).

## **Features Implemented**

- **Snapshot:**
  - Generates a directory map using 2-space indentation.
  - Adds a trailing `/` to directory names in the map.
  - Includes built-in default ignore patterns (e.g., .git, node_modules, **pycache**).
  - Allows adding custom ignore patterns (comma-separated) via GUI.
  - **NEW:** Interactive map exclusion:
    - Clicking a line in the generated map toggles a visual strikethrough.
    - Clicking a directory also toggles its children (cascading).
    - Toggling adds/removes the item(s) from the Custom Ignores field for transparency and persistence.
  - Buttons to manually copy map or save it to a .txt file.
  - **NEW:** Copy to Clipboard respects exclusions from _both_ struck-through lines _and_ the Custom Ignores field.
  - Option to automatically copy the map (with exclusions) to the clipboard on generation or after clicking to exclude.
  - Status feedback label.
  - Informational label showing key default ignores.
- **Scaffold:**
  - Parses multiple map formats: Consistent Spaces (2 or 4), Tabs, Tree-like prefixes (Unicode/ASCII), Generic Indentation (fallback).
  - Auto-detects input format, with manual override via dropdown.
  - **NEW:** Interactive map exclusion:
    - Clicking a line in the input map toggles a visual strikethrough.
    - Clicking a directory also toggles its children (cascading visual only).
  - Creates the directory structure and empty files within a selected base directory, **skipping items corresponding to struck-through lines (including children)**.
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
- **Context Handling:**
  - Can be launched with a directory path (starts Snapshot mode, auto-generates).
  - Can be launched with a file path (starts Scaffold mode, loads file).
  - Can be launched targeting a base directory for scaffolding ("Create Here" workflow - requires context menu setup).

## **Requirements**

- Python 3.x (developed on 3.x, likely compatible with 3.7+)
- tkinter / ttk (usually included with Python standard library)
- pyperclip (for clipboard access)

## **How to Run (from Source \- Current State)**

1. Clone the repository:  
   git clone \<https://github.com/asavschaeffer/dir-snap>  
   cd DirectoryMapper

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

   - You can also test the core logic directly (without GUI) using the test harness within logic.py: python \-m dirmapper.logic

## **Development Plan / To-Do List**

- **Completed / Mostly Done:**
  - \~\~Core MVP Logic (Snapshot one format, Scaffold multiple formats).\~\~
  - \~\~GUI Structure & Basic Functionality.\~\~
  - \~\~Context Handling (Launch Arguments).\~\~
  - \~\~QoL: Status Bars \+ Colors.\~\~
  - \~\~QoL: Default Ignores Label.\~\~
  - \~\~QoL: Clear Buttons (Styled).\~\~
  - \~\~QoL: Open Output Folder Button.\~\~
  - \~\~QoL: Tooltips.\~\~
  - \~\~Scaffold Parsers: Spaces(2/4), Tabs, Tree, Generic Fallback (Implemented).\~\~
  - \~\~Multi-format Scaffold Parsing Structure (Orchestrator, Detector, Helpers).\~\~
- **Up Next (High Priority):**
  - **Configuration File:** Implement saving/loading settings (custom default ignores to add to built-in, last used paths, format preferences) to a persistent file (e.g., JSON/INI in user config dir).
- **Essential for Deployment:**
  - **Distribution Prep (Packaging, Installer, Right-Click Setup):** Package using PyInstaller \--onedir, create an installer (e.g., Inno Setup), finalize and test right-click setup scripts/instructions.
- **Features (Lower Priority):**
  - **Snapshot Output Formats & Emojis:** Add "Output Format" selector (Tree, Tabs, etc.) and "\[ \] Show Emojis" checkbox to Snapshot tab; implement corresponding logic in create_directory_snapshot.
- **Polish (Low Priority):**
  - **Further UI/UX Refinements:** Minor layout/theme adjustments, improved error dialogs.
  - Refine "Open Folder" logic (error handling, platform edge cases).
- **Future / Deferred Ideas:**
  - Interactive Ignore Tree (Checkbox UI in Snapshot tab).
  - Browser Extension Integration.
  - Drag and Drop support for files/folders onto the UI.
  - Advanced Config (Sounds, UI Themes).

## **License**

(Optional: Add your license here, e.g., MIT License)
