# DirSnap: Directory Snapshot & Scaffolder - Technical Documentation (v3.2)

## 1. Overview

**Goal:** A Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.

**Core Features:**

- **Snapshot (Directory -> Map):** Scans a specified directory, including the directory itself as the root element in the output, and generates an indented text map representing its structure. Supports multiple output formats, ignoring specific files/directories (built-in, user-defined defaults via config, and session-specific), and optional file-type specific emojis.
- **Scaffold (Map -> Directory):** Parses an indented text map and creates the corresponding nested directory structure and empty files within a user-selected base directory. Supports multiple common map formats and handles exclusions, including cascading exclusions for directories.

## 2. Architecture & File Structure

The application follows a simple structure separating the entry point, GUI, and backend logic:

```
DirSnap/ # Or project root folder
├── .gitignore
├── README.md
├── requirements.txt
├── main.py         # Application entry point
├── dirsnap/        # Main application package (corrected name)
│   ├── __init__.py
│   ├── app.py      # Tkinter GUI (DirSnapApp class)
│   ├── logic.py    # Backend functions (Snapshot/Scaffold logic)
│   └── utils.py    # Utility functions/constants (config path, app name)
└── scripts/        # OS-specific setup helpers (optional)
    └── ...
```

- **main.py:** Handles initial launch, parses command-line arguments (e.g., a path passed from a context menu), determines the initial mode (Snapshot/Scaffold), instantiates the `DirSnapApp`, and starts the Tkinter main loop.
- **dirsnap/app.py:** Contains the `DirSnapApp` class, built using `tkinter` and `tkinter.ttk`. It manages the UI window, menu bar, notebook/tabs, all widgets, event handling (`_handle_snapshot_map_click`, `_handle_scaffold_map_click`, etc.), configuration loading/saving (`_load_config`, `_save_config`), help actions, and calls functions from `logic.py` (often via background threads using `_start_background_task`). Includes helper classes like `Tooltip` and UI update methods like `_update_status`. Handles interactive exclusion logic (tagging, ignore CSV updates, scaffold exclusion expansion).
- **dirsnap/logic.py:** Contains the core non-GUI logic for snapshotting and scaffolding. Interacts with the filesystem (`os`, `pathlib`) and performs text processing/parsing (`re`, `fnmatch`). Designed to be independent of the GUI. Defines ignore patterns, emoji mappings, and parsing rules.
- **dirsnap/utils.py:** Contains shared constants (`APP_NAME`, `CONFIG_FILENAME`) and utility functions, notably `get_config_path()` for determining the platform-specific path to `config.json`.

## 3. Key Modules & Logic

### 3.1. `logic.py` - Backend

- **Constants:**
  - `DEFAULT_IGNORE_PATTERNS`: Set of default patterns to ignore.
  - `TREE_BRANCH`, `TREE_LAST_BRANCH`, `TREE_PIPE`, `TREE_SPACE`: Constants for Tree format rendering.
  - `FOLDER_EMOJI`, `DEFAULT_FILE_EMOJI`: Default emojis.
  - `FILE_TYPE_EMOJIS`: Dictionary mapping lowercase file extensions to specific emojis.
- **`create_directory_snapshot(root_dir_str, custom_ignore_patterns, user_default_ignores, output_format, show_emojis)`:**
  - Takes root path, optional session ignores, user default ignores (from config), output format, and emoji preference.
  - Merges ignore patterns.
  - Uses `os.walk(topdown=True)` and the combined `ignore_set` for efficient traversal and pruning.
  - Builds an intermediate tree structure (`dict`) in memory representing the directory hierarchy (`{'name': ..., 'is_dir': ..., 'children': [...], 'path': ...}`).
  - **Initiates map generation by calling the recursive helper `build_map_lines_from_tree` with the _root node itself_ at `level=0`**, causing the scanned directory name to appear first in the map.
  - **`build_map_lines_from_tree` (Internal Helper):**
    - Recursively traverses the intermediate tree.
    - Calculates indentation based on `level` and `output_format`.
    - Constructs tree prefixes (`├──`, `└──`, `│  `, `   `) based on `level` and `is_last` sibling status for "Tree" format.
    - If `show_emojis` is true:
      - Uses `FOLDER_EMOJI` for directories.
      - For files, extracts the extension, looks it up (lowercase) in `FILE_TYPE_EMOJIS`, and uses the specific emoji or `DEFAULT_FILE_EMOJI` as a fallback.
    - Appends the formatted line to the `map_lines` list.
- **`create_structure_from_map(map_text, base_dir_str, format_hint, excluded_lines, queue)`:**
  - Main public function for scaffolding. Takes map text, base directory path, format hint, a set of excluded line numbers (from UI clicks), and an optional `queue` for progress updates.
  - Calls `parse_map` to get standardized items `[(level, name, is_dir), ...]`, respecting `excluded_lines`.
  - Calls `create_structure_from_parsed` to build the structure from the parsed items, passing the queue.
  - Returns `(message, success_bool, created_root_name_or_None)`.
- **`parse_map(map_text, format_hint, excluded_lines)`:**
  - Orchestrates parsing based on `format_hint` or auto-detection (`_detect_format`).
  - Selects and calls the appropriate specific parser (`_parse_indent_based`, `_parse_tree_format`, `_parse_generic_indent`).
  - Passes `excluded_lines` to the chosen parser to skip processing those lines.
  - Returns `[(level, item_name, is_directory), ...]` or `None` on error, or `[]` if all lines excluded/comments.
- **`create_structure_from_parsed(parsed_items, base_dir_str, queue)`:**
  - Takes the standardized list output from `parse_map`.
  - Iterates through `parsed_items`. Manages `path_stack` (list of `pathlib.Path` objects) based on `level` changes to track the current parent directory.
  - Performs consistency checks on `level` progression against the `path_stack` depth.
  - Sanitizes `item_name` (`re.sub`, `strip`) for filesystem compatibility.
  - Creates directories (`mkdir(parents=True, exist_ok=True)`) and empty files (`touch(exist_ok=True)`) using `pathlib`.
  - Puts progress updates (`{'type': 'progress', ...}`) into the `queue` if provided.
  - Returns `(message, success_bool, created_root_name_or_None)`.
- **Internal Helper Functions & Parsers:**
  - `_detect_format`: Guesses format ("Tree", "Tabs", "Spaces (2/4)", "Generic", "Unknown").
  - `_parse_indent_based`: Parses maps with consistent space or tab indentation. Uses `_extract_line_components`.
  - `_parse_tree_format`: Parses tree-style formats by analyzing prefix structure (`TREE_PIPE`, `TREE_SPACE`, `TREE_BRANCH`, `TREE_LAST_BRANCH`). Uses `_extract_final_components`.
  - `_parse_generic_indent`: Fallback parser for unknown/inconsistent indentation. Uses `_extract_line_components`.
  - `_extract_final_components`: Helper for tree parser; extracts emoji, name, directory status from the part _after_ structural prefixes. Handles expanded emojis.
  - `_extract_line_components`: Older helper for indent/generic parsers; analyzes a full line for prefixes, emojis, indent. Handles expanded emojis.

### 3.2. `app.py` - Frontend (GUI)

- **`DirSnapApp(tk.Tk)` Class:**
  - Initializes main window, styles, menu, notebook/tabs.
  - Creates widgets (`_create_...`) and arranges them (`_layout_...`). Stores widgets and associated `tk.StringVar`, `tk.BooleanVar`, etc.
  - Loads configuration on startup (`_load_config`).
  - Handles initial state/arguments (`_handle_initial_state`).
  - Saves configuration on exit (`_on_closing` calls `_save_config`).
- **Configuration Methods (`_load_config`, `_save_config`, `_on_closing`, `_open_config_file`):**
  - Load/Save window geometry (`window` section).
  - Load/Save last paths (`snapshot.last_source_dir`, `scaffold.last_base_dir`).
  - Load/Save snapshot preferences (`snapshot.auto_copy`, **`snapshot.output_format`**, **`snapshot.show_emojis`**).
  - Load/Save scaffold format hint (`scaffold.last_format`).
  - Load/Save user default ignores (`user_default_ignores` list).
  - Uses `utils.get_config_path()` to find `config.json`.
  - `_open_config_file` opens `config.json` in the default editor.
- **Snapshot Tab Methods:**
  - `_generate_snapshot`: Validates input, gets settings (format, emojis, ignores), starts `_snapshot_thread_target` via `_start_background_task`.
  - `_handle_snapshot_map_click`:
    - Identifies clicked line and determines if tag should be applied/removed.
    - Uses `_is_directory_heuristic` and `_get_descendant_lines` to find lines to process (clicked + descendants if directory).
    - For each line, **iteratively strips leading Tree prefixes (`TREE_PIPE`, `TREE_SPACE`, `TREE_BRANCH`, `TREE_LAST_BRANCH`) and whitespace**.
    - **Strips leading emoji** (from `ALL_KNOWN_EMOJIS_FOR_STRIPPING`) and subsequent space.
    - Strips trailing `/` and whitespace to get `clean_item_name`.
    - Calls `_update_ignore_csv` with the `clean_item_name`.
    - Toggles strikethrough tag.
  - `_update_ignore_csv`: Updates the `snapshot_ignore_var` (comma-separated string).
  - `_copy_snapshot_to_clipboard`: Gets text, filters based on tags and `snapshot_ignore_var`, copies to clipboard.
  - `_save_snapshot_as`: Saves current text area content to a file.
- **Scaffold Tab Methods:**
  - `_create_structure`:
    - Gets map text, base directory, format hint.
    - Gets initially excluded line numbers based on `TAG_STRIKETHROUGH` in `scaffold_map_input`.
    - **Expands exclusions:**
      - Pre-parses the map text using `logic.parse_map` to get levels/types.
      - Iterates through initially excluded lines. If an excluded line is a directory, recursively finds all descendant lines (lines below it with greater level) using the pre-parsed levels.
      - Adds all found descendant line numbers to the `final_excluded_lines` set.
    - Starts `_scaffold_thread_target` via `_start_background_task`, passing the `final_excluded_lines`.
  - `_handle_scaffold_map_click`: Toggles strikethrough tag on clicked line and its descendants (visual only).
  - `_paste_map_input`, `_load_map_file`, `_browse_scaffold_base_dir`: UI actions.
  - `_show_open_folder_button`, `_open_last_scaffold_folder`: Manage/use the button to open output.
- **Threading/Queue Methods (`_start_background_task`, `_finalize_task_ui`, `_check_..._queue`, `_..._thread_target`):** Manage running backend logic in separate threads using `threading` and `queue` for communication.
- **Click Handler Helpers (`_get_line_info`, `_get_content_range`, `_toggle_tag_on_range`, `_get_descendant_lines`, `_is_directory_heuristic`):** Provide utility functions for text widget interaction and analysis.

## 4. Data Flow

- **Launch:** `main.py` -> Instantiates `DirSnapApp` with context.
- **Initialization:** `DirSnapApp.__init__` sets up UI, calls `_load_config` (loads paths, **snapshot format/emojis**, ignores, etc.), calls `_handle_initial_state`.
- **Snapshot:** User interaction -> `_generate_snapshot` -> `_start_background_task` -> `_snapshot_thread_target` calls `logic.create_directory_snapshot` -> Result via queue -> `_check_snapshot_queue` updates UI. Click -> `_handle_snapshot_map_click` -> Cleans name -> `_update_ignore_csv`.
- **Scaffold:** User interaction -> `_create_structure` -> Gets initial excludes -> **Expands excludes to descendants** -> `_start_background_task` -> `_scaffold_thread_target` calls `logic.create_structure_from_map` (passing expanded excludes, queue) -> Progress/Result via queue -> `_check_scaffold_queue` updates UI. Click -> `_handle_scaffold_map_click` (toggles tags visually).
- **Exit:** User closes window -> `_on_closing` -> `_save_config` writes state (paths, **snapshot format/emojis**, etc.) to `config.json` -> `self.destroy()`.

## 5. Dependencies

- Python 3.x
- Tkinter / ttk (Standard Library)
- os, sys, pathlib, re, fnmatch, subprocess, json, threading, queue (Standard Library)
- pyperclip (External library - `pip install pyperclip`)

## 6. Testing

- Manual testing via the GUI (`python main.py`).
- Isolated logic testing via the test harness in `logic.py` (`python -m dirsnap.logic`).
- Check persistence by changing settings (including Snapshot format/emojis), closing, and reopening.

## 7. Future Directions / To-Do

- **Essential for Deployment:** Packaging (PyInstaller), Installer (Inno Setup), Right-click setup.
- **Polish:** UI/UX Refinements, error handling, documentation.
- **Future:** Browser Extension, Drag & Drop, Advanced Config.
