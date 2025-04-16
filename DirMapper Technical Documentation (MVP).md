# **DirMapper & Scaffolder \- Technical Documentation (MVP v1)**

## **1\. Overview**

**Goal:** A Python desktop utility (using Tkinter) designed to assist users, particularly when interacting with Large Language Models (LLMs), by bridging the gap between filesystem directory structures and their text-based map representations.  
**Core Features:**

* **Snapshot (Directory \-\> Map):** Scans a specified directory and generates an indented text map representing its structure (folders and files), suitable for copying. Includes options for ignoring specific files/directories.  
* **Scaffold (Map \-\> Directory):** Parses an indented text map and creates the corresponding nested directory structure and empty files within a user-selected base directory on the filesystem. Supports multiple common map formats.

## **2\. Architecture & File Structure**

The application follows a simple structure separating the entry point, GUI, and backend logic:  
DirectoryMapper/  
├── .gitignore  
├── README.md  
├── requirements.txt  
├── main.py             \# Application entry point  
├── dirmapper/          \# Main application package  
│   ├── \_\_init\_\_.py  
│   ├── app.py          \# Tkinter GUI (DirMapperApp class)  
│   ├── logic.py        \# Backend functions (Snapshot/Scaffold logic)  
│   └── utils.py        \# Utility functions/constants (currently minimal)  
└── scripts/            \# OS-specific setup helpers (for future use)  
    └── ...

* **main.py**: Handles initial launch, parses command-line arguments (e.g., a path passed from a context menu), determines the initial mode (Snapshot/Scaffold), instantiates the DirMapperApp, and starts the Tkinter main loop.  
* **dirmapper/app.py**: Contains the DirMapperApp class, built using tkinter and tkinter.ttk. It manages the UI window, tabs (Snapshot/Scaffold), all widgets (buttons, entries, text areas, labels, combobox), event handling (button clicks, etc.), and calls functions from logic.py to perform backend tasks. It also includes helper classes/functions like Tooltip.  
* **dirmapper/logic.py**: Contains the core non-GUI logic for snapshotting and scaffolding. It interacts with the filesystem (os, pathlib) and performs text processing/parsing (re). It is designed to be independent of the GUI.  
* **dirmapper/utils.py**: (Currently minimal/unused) Intended place for shared constants or utility functions if needed later (e.g., config file handling).

## **3\. Key Modules & Logic**

### **3.1. logic.py \- Backend**

* **create\_directory\_snapshot(root\_dir\_str, custom\_ignore\_patterns)**:  
  * Takes a root directory path and optional custom ignore patterns.  
  * Combines custom ignores with DEFAULT\_IGNORE\_PATTERNS.  
  * Uses os.walk(topdown=True) to efficiently traverse the directory.  
  * Builds an intermediate tree structure (list of dictionaries) in memory, respecting ignores by pruning (dirs\[:\] \= ...) during the walk. This ensures correct hierarchy representation.  
  * Recursively traverses the in-memory tree (build\_map\_lines\_from\_tree) to generate the final output string.  
  * Formats output with consistent spacing (DEFAULT\_SNAPSHOT\_SPACES) and adds a trailing / to directory names.  
* **create\_structure\_from\_map(map\_text, base\_dir\_str, format\_hint)**:  
  * The main public function called by the GUI for scaffolding.  
  * Takes the map text, the target base directory path, and a format hint.  
  * Calls parse\_map to get a standardized list of parsed items.  
  * If parsing succeeds, calls create\_structure\_from\_parsed to build the filesystem structure.  
  * Returns a (message, success\_status) tuple.  
* **parse\_map(map\_text, format\_hint)**:  
  * Orchestrates the parsing process.  
  * Calls \_detect\_format if format\_hint is "Auto-Detect".  
  * Selects and calls the appropriate specific parser (\_parse\_indent\_based, \_parse\_tree\_format, \_parse\_generic\_indent) based on the determined format.  
  * Returns a list of tuples: \[(level, item\_name, is\_directory), ...\] or None on failure.  
* **\_detect\_format(map\_text, sample\_lines)**:  
  * Analyzes the first few lines to guess the format ("Tree", "Tabs", "Spaces (2)", "Spaces (4)", "Generic") based on prefixes and indentation patterns.  
* **\_parse\_indent\_based(map\_text, spaces\_per\_level, use\_tabs)**:  
  * Parses maps using consistent space or tab indentation.  
  * Calculates level based on leading\_chars // indent\_unit.  
  * Validates indentation consistency.  
  * Determines is\_directory based on trailing /.  
* **\_parse\_tree\_format(map\_text)**:  
  * Parses maps using tree-like prefixes (e.g., ├──, | , |-).  
  * Strips known prefix characters (TREE\_PREFIX\_CHARS\_TO\_STRIP) to find the item name.  
  * Uses the overall indent width (starting column of the name) and a dynamic mapping (indent\_map) to determine the level, making it flexible to different tree styles.  
  * Determines is\_directory based on trailing /.  
* **\_parse\_generic\_indent(map\_text)**:  
  * Fallback parser for unknown or inconsistent formats.  
  * Strips common list/prefix characters (PREFIX\_STRIP\_RE\_GENERIC).  
  * Uses the dynamic indent mapping (indent\_map) based on overall indent width to determine level.  
  * Determines is\_directory based on trailing /.  
* **create\_structure\_from\_parsed(parsed\_items, base\_dir\_str)**:  
  * Takes the standardized list output from any parser.  
  * Iterates through the list, managing a path\_stack (list of pathlib.Path objects) based on level changes to track the current parent directory.  
  * Uses Path.mkdir(parents=True, exist\_ok=True) and Path.touch(exist\_ok=True) to create directories and empty files.

### **3.2. app.py \- Frontend (GUI)**

* **DirMapperApp(tk.Tk)** Class:  
  * Initializes the main window, styles (ttk.Style), and notebook/tabs.  
  * Calls helper methods (\_create\_..., \_layout\_...) to build the UI.  
  * Handles initial state based on arguments from main.py (\_handle\_initial\_state).  
* **\_create\_...\_widgets()** Methods: Define and configure all tkinter/ttk widgets (Labels, Entries, Buttons, ScrolledText, Combobox, Checkbutton) for each tab, storing them as instance attributes (e.g., self.snapshot\_dir\_entry). Includes creation of Tooltip instances and styled "Clear" buttons.  
* **\_layout\_...\_widgets()** Methods: Arrange widgets within their parent frames using the .grid() geometry manager. Uses columnconfigure and rowconfigure with weight for responsive resizing. Clear buttons are placed in the same grid cell as entry fields using sticky=tk.E.  
* **Event Handler Methods (\_browse\_..., \_generate\_snapshot, \_create\_structure, etc.):**  
  * Bound to button commands.  
  * Get input values from UI widgets (using associated tk.StringVar etc.).  
  * Perform basic input validation (e.g., check if paths are selected).  
  * Call the corresponding functions in logic.py to perform backend actions.  
  * Update the UI based on results (populate text areas, update status bar using \_update\_status).  
  * Display errors using messagebox.  
  * Handle clipboard operations using pyperclip.  
  * Handle file dialogs using filedialog.  
  * Handle opening the output folder using os.startfile/subprocess.run.  
* **\_update\_status(...)**: Helper method to update the status bar labels on either tab with appropriate messages and colors (Red/Green/Default).  
* **Tooltip** Class: Helper class to display pop-up tooltips on widget hover.

## **4\. Data Flow**

1. **Launch:** main.py runs, checks sys.argv, instantiates DirMapperApp with optional initial path/mode.  
2. **Initialization:** DirMapperApp.\_\_init\_\_ sets up UI. \_handle\_initial\_state selects tab, pre-fills fields, potentially triggers initial snapshot.  
3. **Snapshot:** User selects dir (Browse/context) \-\> Enters ignores \-\> Clicks Generate \-\> \_generate\_snapshot called \-\> gets inputs \-\> calls logic.create\_directory\_snapshot \-\> gets map string \-\> updates output text area \-\> updates status \-\> potentially copies to clipboard. Copy/Save buttons also interact with output area.  
4. **Scaffold:** User pastes/loads map \-\> Selects base dir \-\> Selects format hint \-\> Clicks Create \-\> \_create\_structure called \-\> gets inputs \-\> calls logic.create\_structure\_from\_map (which calls parse\_map, which calls specific parser) \-\> gets result tuple \-\> updates status \-\> potentially enables "Open Folder" button.

## **5\. Dependencies**

* Python 3.x  
* Tkinter / ttk (Standard Library)  
* os, sys, pathlib, re, fnmatch, subprocess (Standard Library)  
* pyperclip (External library \- pip install pyperclip)

## **6\. Testing**

* Manual testing via the GUI (python main.py).  
* Isolated logic testing via the test harness in if \_\_name\_\_ \== '\_\_main\_\_': block of logic.py (python \-m dirmapper.logic).

## **7\. Future Directions / To-Do**

* Configuration File (Save/load ignores, paths, preferences).  
* Snapshot Output Formats (Tree, Tabs, etc.) \+ Emoji option.  
* Distribution (PyInstaller packaging, Installer creation, Right-click setup).  
* UI/UX Polish (Themes, advanced styling).  
* Advanced Features (Interactive Ignore Tree, Browser Extension).