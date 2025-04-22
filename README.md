# DirSnap: Directory Snapshot & Scaffolder

A simple Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.

## Description

This tool has two main functions:

1.  **Snapshot (Directory -> Map):** Scans an existing directory on your filesystem (including the directory itself as the root) and generates a text-based map representing its structure (folders and files), suitable for copying. Includes options for output format (Standard Indent, Tabs, Tree), ignoring specific files/directories, and optionally including file/folder emojis based on file type.
2.  **Scaffold (Map -> Directory):** Parses an indented text map (in various common formats) and creates the corresponding nested directory structure and empty files within a user-selected base directory on the filesystem.

## Current Status (v3.2.1)

Core functionality is complete and packaged for basic distribution. Includes snapshot generation with root dir/emojis, multi-format scaffolding, config persistence, and interactive exclusion. Next steps involve creating a proper installer and refining context menu integration.

## Features Implemented

- **Snapshot:**
  - Generates directory maps starting with the selected directory as the root.
  - Multiple output formats: Standard Indent (2-space), Tabs, or Tree (preference saved in config).
  - Option to include leading emojis based on file type (preference saved in config).
  - Adds a trailing `/` to directory names in the map.
  - Built-in default ignore patterns + loads user-defined defaults from `config.json`.
  - Allows custom ignore patterns per run via GUI.
  - Runs in a background thread with progress bar.
  - **Interactive map exclusion:** Clicking lines/directories toggles strikethrough, adds _clean_ item name to ignore list (handles prefixes/emojis), respects cascade.
  - Copy to Clipboard (respects exclusions) / Save Map As buttons.
  - Auto-copy option (preference saved in config).
- **Scaffold:**
  - Parses multiple map formats (Auto-Detect, Spaces, Tabs, Tree, Generic). Format hint saved in config.
  * Runs in a background thread with progress bar.
  - **Interactive map exclusion:** Clicking lines/directories toggles strikethrough; creation process skips excluded items _and their descendants_.
  * Paste/Load map input.
  * "Open Output Folder" button on success.
- **GUI & Config:**
  - Tkinter/ttk UI with Snapshot/Scaffold tabs.
  - File/Directory browsers, Clear buttons, Tooltips, Status bars.
  - Menu Bar (File, Edit->Preferences, Help->README/About).
  - Settings persistence (`config.json`) for paths, preferences, window state, user ignores.
  - Context Handling (launch via path for Snapshot or Scaffold).
  - **Application Icon:** Custom icon set for executable and window title bar (Taskbar icon may still show default Tkinter icon - known issue).
- **Packaging:**
  - Basic standalone executable created using PyInstaller (`--onedir`).

## Requirements

- Python 3.x (developed on 3.x)
- tkinter / ttk (usually included with Python)
- pyperclip (for clipboard)

## Installation / Running (v3.2.1 - Zip Distribution)

1.  **Download:** Obtain the `DirSnap-v3.2.1.zip` (or `.7z`) file (e.g., from the GitHub Releases page).
2.  **Extract:** Unzip the entire archive to a location on your computer (e.g., your Desktop or Downloads folder). This will create a `DirSnap` folder.
3.  **Run:** Open the extracted `DirSnap` folder and double-click `DirSnap.exe` to launch the application. **Do not move `DirSnap.exe` out of this folder**, as it needs the other files alongside it to work.

**Context Menu Setup (Manual):**

To enable right-clicking on folders/files to use DirSnap:

- **Windows:** Follow the instructions to modify the registry using the `setup_windows_right_click.reg` file located in the `scripts` folder (you may need to edit the file first to ensure the path to `DirSnap.exe` is correct for where you extracted the application). **Requires Administrator privileges.**
- **macOS:** Follow the instructions in `scripts/setup_macos_service_instructions.md` to create a Quick Action using Automator.
- **Linux:** Follow the instructions in `scripts/setup_linux_action_instructions.md` for your specific desktop environment/file manager.

## How to Run (from Source)

1.  Clone the repository.
2.  (Recommended) Create and activate a virtual environment: `python -m venv venv`, then activate it (`.\venv\Scripts\activate` or `source venv/bin/activate`).
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Run: `python main.py`.

## Development Plan / To-Do List

- **Completed / Mostly Done:**
  - [x] Core MVP Logic & GUI Structure.
  - [x] Context Handling & QoL Features (Status, Clear, Tooltips, Open Folder).
  - [x] Multi-Format Parsing & Snapshotting.
  - [x] Interactive Exclusion (Snapshot & Scaffold) w/ Cascade & Prefix Stripping.
  - [x] Background Threading & Progress Bars.
  - [x] Config File Persistence (Paths, Prefs, Ignores, Window State).
  - [x] Help Menu & About Dialog.
  - [x] Snapshot: Root Dir included, Expanded Emojis, Config options saved.
  - [x] Scaffold: Descendant Exclusion handled.
  - [x] Basic Packaging (`--onedir` executable created).
  - [x] Application Icon (Window Title / File, Taskbar issue pending).
- **Up Next:**
  - **Distribution Prep:**
    - Create Windows Installer (Inno Setup) to automate installation, shortcut creation, and potentially context menu setup (`.reg` execution).
    - Refine/Test Context Menu Setup scripts/instructions for all platforms.
  - **Polish:**
    - Investigate remaining Taskbar icon issue on Windows.
    - Further UI/UX Refinements (Layout, Error Dialogs).
    - Refine "Open Folder" logic (edge cases).
    - Final Documentation Review.
- **Future / Deferred Ideas:**
  - Browser Extension Integration.
  - Drag and Drop support.
  - Advanced Config Options.

## License
