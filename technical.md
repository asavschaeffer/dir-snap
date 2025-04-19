# **DirSnap: Directory Snapshot & Scaffolder - Technical Documentation (v3.1)**

## **1. Overview**

**Goal:** A Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.
**Core Features:**

- **Snapshot (Directory -> Map):** Scans a specified directory and generates an indented text map representing its structure (folders and files), suitable for copying. Includes options for ignoring specific files/directories (built-in, user-defined defaults via config, and session-specific).
- **Scaffold (Map -> Directory):** Parses an indented text map and creates the corresponding nested directory structure and empty files within a user-selected base directory on the filesystem. Supports multiple common map formats.

## **2. Architecture & File Structure**

The application follows a simple structure separating the entry point, GUI, and backend logic:
DirSnap/ # Or project root folder
├── .gitignore
├── README.md
├── requirements.txt
├── main.py # Application entry point
├── DirSnap/ # Main application package (FOLDER RENAMED)
│ ├── **init**.py
│ ├── app.py # Tkinter GUI (DirSnapApp class)
│ ├── logic.py # Backend functions (Snapshot/Scaffold logic)
│ └── utils.py # Utility functions/constants (config path, app name)
└── scripts/ # OS-specific setup helpers (for future use)
└── ...

- **main.py**: Handles initial launch, parses command-line arguments (e.g., a path passed from a context menu), determines the initial mode (Snapshot/Scaffold), instantiates the `DirSnapApp`, and starts the Tkinter main loop.
- **DirSnap/app.py**: Contains the `DirSnapApp` class (CLASS RENAMED), built using tkinter and tkinter.ttk. It manages the UI window, menu bar, notebook/tabs (Snapshot/Scaffold), all widgets, event handling, configuration loading/saving (`_load_config`, `_save_config`, `_on_closing`), help actions (`_show_about`, `_view_readme`), and calls functions from `logic.py` to perform backend tasks, often via background threads. Includes helper classes like `Tooltip`.
- **DirSnap/logic.py**: Contains the core non-GUI logic for snapshotting and scaffolding. It interacts with the filesystem (`os`, `pathlib`) and performs text processing/parsing (`re`). Designed to be independent of the GUI. Handles ignore pattern merging.
- **DirSnap/utils.py**: Contains shared constants (`APP_NAME`, `CONFIG_FILENAME`) and utility functions, notably `get_config_path()` for determining the platform-specific path to `config.json`.

## **3. Key Modules & Logic**

### **3.1. logic.py - Backend**

- **create_directory_snapshot(root_dir_str, custom_ignore_patterns, user_default_ignores)**: (Updated Signature)
  - Takes root path, optional session ignores, and optional user default ignores (from config).
  - Merges `DEFAULT_IGNORE_PATTERNS`, `user_default_ignores`, and `custom_ignore_patterns` into a single `ignore_set`.
  - Uses `os.walk(topdown=True)` and the combined `ignore_set` for efficient traversal and pruning.
  - Builds an intermediate tree, then generates the map string (MVP format currently).
  - Adds trailing `/` to directory names.
- **create_structure_from_map(map_text, base_dir_str, format_hint, excluded_lines, queue)**: (Updated Signature)
  - Main public function for scaffolding. Takes map, base dir, format hint, set of excluded line numbers (from UI clicks), and optional queue for progress updates.
  - Calls `parse_map` to get standardized items, respecting `excluded_lines`.
  - Calls `create_structure_from_parsed` to build the structure, passing the `queue` for progress reporting.
  - Returns `(message, success_status)`.
- **parse_map(map_text, format_hint, excluded_lines)**: (Updated Signature)
  - Orchestrates parsing based on format hint or auto-detection (`_detect_format`).
  - Skips lines specified in `excluded_lines`.
  - Selects and calls the appropriate specific parser (`_parse_...`), passing `excluded_lines`.
  - Returns `[(level, item_name, is_directory), ...]` or `None`.
- **(Internal Parsers: `_detect_format`, `_parse_indent_based`, `_parse_tree_format`, `_parse_generic_indent`)**: Handle specific format detection and parsing logic, respecting `excluded_lines`.
- **create_structure_from_parsed(parsed_items, base_dir_str, queue)**: (Updated Signature)
  - Takes the standardized list output from `parse_map`.
  - Iterates, manages `path_stack` based on level.
  - Creates directories/files using `pathlib`.
  - Puts progress updates (`{'type': 'progress', 'current': i, 'total': total}`) into the `queue` if provided.

### **3.2. app.py - Frontend (GUI)**

- **DirSnapApp(tk.Tk)** Class: (CLASS RENAMED)
  - Initializes main window, styles, menu bar (`File`, `Edit`, `Help`), notebook/tabs.
  - Creates widgets (`_create_..._widgets`) and arranges them (`_layout_..._widgets`).
  - **NEW:** Loads configuration on startup (`_load_config`).
  - Handles initial state from args (`_handle_initial_state`).
  - **NEW:** Saves configuration on exit (via `_on_closing` bound to `WM_DELETE_WINDOW` protocol, which calls `_save_config`).
- **(Widget Creation/Layout Methods: `_create_...`, `_layout_...`)**: Define, configure, and arrange all tkinter/ttk widgets, including tooltips and clear buttons. Store widgets and associated variables (e.g., `self.snapshot_dir_var`) as instance attributes.
- **(Event Handler Methods: `_browse_...`, `_generate_snapshot`, `_create_structure`, etc.)**: Bound to buttons/menu commands. Get inputs, validate, call `logic.py` functions (often via `_start_background_task`), update UI (`_update_status`), handle dialogs/clipboard.
- **(Threading/Queue Methods: `_start_background_task`, `_finalize_task_ui`, `_check_..._queue`, `_snapshot_thread_target`, `_scaffold_thread_target`)**: Manage running backend logic in separate threads to prevent UI freezing, using queues for communication (results, progress updates).
- **(Configuration Methods: `_load_config`, `_save_config`, `_on_closing`, `_open_config_file`)**: Handle loading settings from `config.json` (via `utils.get_config_path`), applying them to UI variables/window geometry, gathering current state, and saving back to `config.json` on exit. `_open_config_file` handles the "Edit -> Preferences..." menu action.
- **(Help Methods: `_show_about`, `_view_readme`)**: Handle the "Help" menu actions, displaying an About box or opening the README file.
- **(Other Helpers: `_update_status`, `Tooltip`, `_get_line_info`, `_toggle_tag_on_range`, etc.)**: Provide utility functions for status updates, tooltips, text widget interaction, etc.

## **4. Data Flow**

1.  **Launch:** `main.py` runs, checks `sys.argv`, instantiates `DirSnapApp` with optional initial path/mode.
2.  **Initialization:** `DirSnapApp.__init__` sets up UI structure (menus, notebook), creates widgets/variables, calls `_load_config` to apply saved settings, calls `_layout_widgets`, binds closing protocol to `_on_closing`, then calls `_handle_initial_state`.
3.  **Snapshot:** User selects dir -> Enters ignores -> Clicks Generate -> `_generate_snapshot` starts background task -> `_snapshot_thread_target` calls `logic.create_directory_snapshot` (passing loaded user ignores) -> Result put in queue -> `_check_snapshot_queue` updates UI.
4.  **Scaffold:** User pastes/loads map -> Selects base dir -> Selects format hint -> Clicks Create -> `_create_structure` starts background task -> `_scaffold_thread_target` calls `logic.create_structure_from_map` (passing exclusions, queue) -> Progress/Result put in queue -> `_check_scaffold_queue` updates UI (progress bar, status, open button).
5.  **Exit:** User clicks close button -> `_on_closing` is called -> `_save_config` gathers current state and writes to `config.json` (via `utils.get_config_path`) -> `self.destroy()` closes the app.

## **5. Dependencies**

- Python 3.x
- Tkinter / ttk (Standard Library)
- os, sys, pathlib, re, fnmatch, subprocess, json, threading, queue (Standard Library)
- pyperclip (External library - `pip install pyperclip`)

## **6. Testing**

- Manual testing via the GUI (`python main.py`).
- Isolated logic testing via the test harness in `logic.py` (`python -m DirSnap.logic`).
- Check persistence by changing settings, closing, and reopening the app.

## **7. Future Directions / To-Do**

- **Snapshot Output Formats & Emojis:** Add output format selection (Tree, Tabs, etc.) and emoji option to Snapshot tab and config.
- **Distribution Prep:** Packaging (PyInstaller), Installer (Inno Setup), Right-click setup.
- **UI/UX Polish:** Themes, advanced styling, error handling.
- **Advanced Features:** Interactive Ignore Tree, Browser Extension, Drag & Drop.
- **Documentation:** Refine README and Technical Docs further.
