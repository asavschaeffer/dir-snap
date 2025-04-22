# filename: dirsnap/app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkFont # Import font submodule
import pyperclip # Dependency: pip install pyperclip
import json
from pathlib import Path
import sys
import os
import re # Import re for scaffold exclusion logic
import subprocess
import threading
import queue
# Removed fnmatch, shutil, time as they seem unused directly in app.py
# Keeping for logic import:
import fnmatch
import shutil
import time

# --- Consolidated Import Logic for logic and utils ---
try:
    # Attempt relative imports (standard when running as part of the package)
    from . import logic
    from .utils import get_config_path

    # Define constants needed from logic after successful import
    FOLDER_EMOJI = logic.FOLDER_EMOJI
    DEFAULT_FILE_EMOJI = logic.DEFAULT_FILE_EMOJI
    FILE_TYPE_EMOJIS = logic.FILE_TYPE_EMOJIS
    TREE_BRANCH = logic.TREE_BRANCH
    TREE_LAST_BRANCH = logic.TREE_LAST_BRANCH
    TREE_PIPE = logic.TREE_PIPE # Added
    TREE_SPACE = logic.TREE_SPACE # Added
    # Generate the list of all possible emojis for stripping
    ALL_KNOWN_EMOJIS_FOR_STRIPPING = list(set([FOLDER_EMOJI, DEFAULT_FILE_EMOJI] + list(FILE_TYPE_EMOJIS.values())))
    print("Successfully imported logic and utils using relative paths.")

except ImportError:
    # Relative import failed, likely running app.py directly
    print("Warning: Relative import failed. Attempting direct import (likely running app.py directly).")
    try:
        # Attempt direct imports
        import logic
        import utils

        # Define constants needed from logic
        FOLDER_EMOJI = logic.FOLDER_EMOJI
        DEFAULT_FILE_EMOJI = logic.DEFAULT_FILE_EMOJI
        FILE_TYPE_EMOJIS = logic.FILE_TYPE_EMOJIS
        TREE_BRANCH = logic.TREE_BRANCH
        TREE_LAST_BRANCH = logic.TREE_LAST_BRANCH
        TREE_PIPE = logic.TREE_PIPE # Added
        TREE_SPACE = logic.TREE_SPACE # Added
        ALL_KNOWN_EMOJIS_FOR_STRIPPING = list(set([FOLDER_EMOJI, DEFAULT_FILE_EMOJI] + list(FILE_TYPE_EMOJIS.values())))
        # Get function from utils
        get_config_path = utils.get_config_path
        print("Successfully imported logic and utils using direct paths.")

    except ImportError as direct_import_error:
        # Both relative and direct imports failed
        print(f"ERROR: Failed to import logic/utils via relative or direct path: {direct_import_error}")
        print("!!! Functionality will be severely limited. Using fallbacks. !!!")

        # Define fallbacks for constants
        FOLDER_EMOJI = "📁"
        DEFAULT_FILE_EMOJI = "📄"
        FILE_TYPE_EMOJIS = {}
        TREE_BRANCH = "├── "
        TREE_LAST_BRANCH = "└── "
        TREE_PIPE = "│   " # Added fallback
        TREE_SPACE = "    " # Added fallback
        ALL_KNOWN_EMOJIS_FOR_STRIPPING = [FOLDER_EMOJI, DEFAULT_FILE_EMOJI]

        # Define dummy function for get_config_path
        def get_config_path():
            print("FATAL: get_config_path function is not available due to import errors.")
            messagebox.showerror("Import Error", "Cannot load/save config. Critical components failed to import.")
            return None

        logic = None

# --- Application Constants ---
APP_VERSION = "3.2.1" # Incremented version

# --- Tooltip Helper Class ---
class Tooltip:
    """
    Creates a tooltip (pop-up) window for a Tkinter widget.
    """
    def __init__(self, widget, text, delay=500, wraplength=180):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.widget.bind("<Enter>", self.schedule_tooltip, add='+')
        self.widget.bind("<Leave>", self.hide_tooltip, add='+')
        self.widget.bind("<ButtonPress>", self.hide_tooltip, add='+')
        self.tip_window = None
        self.id = None

    def schedule_tooltip(self, event=None):
        self.hide_tooltip()
        self.id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength=self.wraplength, padx=4, pady=2)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        scheduled_id = self.id
        self.id = None
        if scheduled_id:
            try: self.widget.after_cancel(scheduled_id)
            except ValueError: pass
        tip = self.tip_window
        self.tip_window = None
        if tip:
            try: tip.destroy()
            except tk.TclError: pass

# --- DirSnapApp Class ---
class DirSnapApp(tk.Tk):
    # --- Constants ---
    TAG_STRIKETHROUGH = "strikethrough"
    QUEUE_MSG_PROGRESS = "progress"
    QUEUE_MSG_RESULT = "result"
    TAB_SNAPSHOT = "snapshot"
    TAB_SCAFFOLD = "scaffold"
    # --- End Constants ---

    def __init__(self, initial_path=None, initial_mode='snapshot'):
        super().__init__()

        # --- Initialize attributes ---
        self.user_default_ignores = []
        self.last_scaffold_path = None
        self.scaffold_queue = queue.Queue()
        self.snapshot_queue = queue.Queue()
        self.scaffold_thread = None
        self.snapshot_thread = None
        self.initial_path = Path(initial_path) if initial_path else None
        self.initial_mode = initial_mode

        self.title("DirSnap") # Simplified Title
        self.minsize(550, 450)

        # --- Create Menu Bar ---
        self.menu_bar = tk.Menu(self)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_closing)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="Preferences...", command=self._open_config_file)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="View README", command=self._view_readme)
        self.help_menu.add_command(label="About DirSnap", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.config(menu=self.menu_bar)

        self._configure_styles()

        # --- Main UI Structure ---
        self.notebook = ttk.Notebook(self)
        self.snapshot_frame = ttk.Frame(self.notebook, padding="10")
        self.scaffold_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.snapshot_frame, text='Snapshot (Dir -> Map)')
        self.notebook.add(self.scaffold_frame, text='Scaffold (Map -> Dir)')
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # --- Create Widgets ---
        self._create_snapshot_widgets()
        self._create_scaffold_widgets()

        self._load_config() # Load config before layout might affect default sizes

        # --- Layout Widgets ---
        self._layout_snapshot_widgets()
        self._layout_scaffold_widgets()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(50, self._handle_initial_state) # Handle context args after UI setup

    def _configure_styles(self):
        """Configure custom ttk styles."""
        style = ttk.Style(self)
        try: text_color = style.lookup('TLabel', 'foreground')
        except tk.TclError: text_color = 'black'
        style.configure('ClearButton.TButton', foreground='grey', borderwidth=0, relief='flat', padding=0)
        style.map('ClearButton.TButton', foreground=[('active', text_color), ('pressed', text_color)])

    # --- Configuration Methods ---
    def _load_config(self):
        """Loads settings from the configuration file."""
        config_path = get_config_path()
        if not config_path or not config_path.exists():
            print("Info: Configuration file not found. Using default settings.")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f: config_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error: Failed to load or parse config file '{config_path}': {e}")
            messagebox.showwarning("Config Load Error", f"Could not load config.\nUsing defaults.\n\nError: {e}", parent=self)
            return

        window_conf = config_data.get("window", {})
        width, height = window_conf.get("width", 550), window_conf.get("height", 450)
        x_pos, y_pos = window_conf.get("x_pos"), window_conf.get("y_pos")
        if x_pos is not None and y_pos is not None: self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        else: self.geometry(f"{width}x{height}")

        snapshot_conf = config_data.get("snapshot", {})
        last_source = snapshot_conf.get("last_source_dir")
        if last_source and not self.initial_path: self.snapshot_dir_var.set(last_source)
        self.snapshot_auto_copy_var.set(snapshot_conf.get("auto_copy", False))
        self.snapshot_format_var.set(snapshot_conf.get("output_format", "Standard Indent"))
        self.snapshot_show_emojis_var.set(snapshot_conf.get("show_emojis", False))

        scaffold_conf = config_data.get("scaffold", {})
        last_base = scaffold_conf.get("last_base_dir")
        if last_base and not (self.initial_path and self.initial_mode == 'scaffold_here'): self.scaffold_base_dir_var.set(last_base)
        self.scaffold_format_var.set(scaffold_conf.get("last_format", "Auto-Detect"))

        loaded_ignores = config_data.get("user_default_ignores", [])
        self.user_default_ignores = loaded_ignores if isinstance(loaded_ignores, list) else []
        if not isinstance(loaded_ignores, list): print(f"Warning: Invalid user_default_ignores in config: {loaded_ignores}")

        print(f"Info: Configuration loaded successfully from {config_path}")

    def _save_config(self):
        """Saves current settings to the configuration file."""
        config_path = get_config_path()
        if not config_path:
            print("Error: Could not determine config path. Settings not saved.")
            return

        settings = {"version": 1, "window": {}, "snapshot": {}, "scaffold": {}, "user_default_ignores": self.user_default_ignores}

        try:
            geo = self.geometry()
            size, x, y = geo.split('+')
            w, h = size.split('x')
            settings["window"] = {"width": int(w), "height": int(h), "x_pos": int(x), "y_pos": int(y)}
        except Exception as e:
            print(f"Warning: Could not parse geometry '{self.geometry()}': {e}. Using defaults/previous.")
            settings["window"] = {"width": 550, "height": 450, "x_pos": None, "y_pos": None} # Simple fallback

        settings["snapshot"] = {
            "last_source_dir": self.snapshot_dir_var.get(),
            "auto_copy": self.snapshot_auto_copy_var.get(),
            "output_format": self.snapshot_format_var.get(),
            "show_emojis": self.snapshot_show_emojis_var.get()
        }
        settings["scaffold"] = {
            "last_base_dir": self.scaffold_base_dir_var.get(),
            "last_format": self.scaffold_format_var.get()
        }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4)
            print(f"Info: Configuration saved successfully to {config_path}")
        except (OSError, TypeError) as e: print(f"Error: Failed to save config file '{config_path}': {e}")

    def _on_closing(self):
        print("Info: Closing application, saving configuration...")
        self._save_config()
        self.destroy()

    def _open_config_file(self):
        config_path = get_config_path()
        if not config_path: messagebox.showerror("Error", "Could not determine config path.", parent=self); return
        if not config_path.is_file():
            if messagebox.askyesno("Config Not Found", f"Config file not found:\n{config_path}\n\nCreate it now?", parent=self):
                self._save_config()
                if not config_path.is_file(): messagebox.showerror("Error", f"Failed to create:\n{config_path}", parent=self); return
            else: return
        try:
            print(f"Info: Opening config file: {config_path}")
            if sys.platform == "win32": os.startfile(str(config_path))
            elif sys.platform == "darwin": subprocess.run(['open', str(config_path)], check=True)
            else: subprocess.run(['xdg-open', str(config_path)], check=True)
        except Exception as e: messagebox.showerror("Error Opening File", f"Could not open file:\n{config_path}\n\n{e}", parent=self)

    # --- Widget Creation Methods ---
    def _create_snapshot_widgets(self):
        frame = self.snapshot_frame
        ttk.Label(frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Label(frame, text="Custom Ignores (comma-sep):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        try: defaults = sorted(list(logic.DEFAULT_IGNORE_PATTERNS))[:4]; txt = f"Ignoring defaults like: {', '.join(defaults)}, ..."; tip = "Also ignoring:\n" + "\n".join(sorted(list(logic.DEFAULT_IGNORE_PATTERNS)))
        except: txt, tip = "Ignoring default patterns...", "Defaults unavailable."
        self.snapshot_default_ignores_label = ttk.Label(frame, text=txt, foreground="grey")
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5))
        Tooltip(self.snapshot_default_ignores_label, tip)
        self.snapshot_dir_var = tk.StringVar()
        self.snapshot_dir_entry = ttk.Entry(frame, textvariable=self.snapshot_dir_var, width=50)
        self.snapshot_browse_button = ttk.Button(frame, text="Browse...", command=self._browse_snapshot_dir)
        self.snapshot_clear_dir_button = ttk.Button(frame, text="X", width=2, command=lambda: self.snapshot_dir_var.set(''), style='ClearButton.TButton')
        Tooltip(self.snapshot_browse_button, "Select root directory.")
        Tooltip(self.snapshot_clear_dir_button, "Clear path")
        self.snapshot_ignore_var = tk.StringVar()
        self.snapshot_ignore_entry = ttk.Entry(frame, textvariable=self.snapshot_ignore_var, width=50)
        self.snapshot_clear_ignore_button = ttk.Button(frame, text="X", width=2, command=lambda: self.snapshot_ignore_var.set(''), style='ClearButton.TButton')
        Tooltip(self.snapshot_ignore_entry, "Patterns to ignore (e.g., .git, *.log)")
        Tooltip(self.snapshot_clear_ignore_button, "Clear ignores")
        ttk.Label(frame, text="Output Format:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_format_var = tk.StringVar(value="Standard Indent")
        self.snapshot_format_options = ["Standard Indent", "Tree", "Tabs"]
        self.snapshot_format_combo = ttk.Combobox(frame, textvariable=self.snapshot_format_var, values=self.snapshot_format_options, state='readonly', width=18)
        Tooltip(self.snapshot_format_combo, "Select map output format.")
        self.snapshot_show_emojis_var = tk.BooleanVar(value=False)
        self.snapshot_show_emojis_check = ttk.Checkbutton(frame, text="Emojis 📁📄", variable=self.snapshot_show_emojis_var)
        Tooltip(self.snapshot_show_emojis_check, "Prepend emojis.")
        self.snapshot_regenerate_button = ttk.Button(frame, text="Generate / Regenerate Map", command=self._generate_snapshot)
        Tooltip(self.snapshot_regenerate_button, "Generate map.")
        self.snapshot_auto_copy_var = tk.BooleanVar(value=False)
        self.snapshot_auto_copy_check = ttk.Checkbutton(frame, text="Auto-copy on generation/click", variable=self.snapshot_auto_copy_var)
        Tooltip(self.snapshot_auto_copy_check, "Auto-copy map.")
        self.snapshot_map_output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED)
        self.snapshot_map_output.tag_configure(self.TAG_STRIKETHROUGH, overstrike=True, foreground="grey50")
        self.snapshot_map_output.bind("<Button-1>", self._handle_snapshot_map_click)
        Tooltip(self.snapshot_map_output, "Click line to toggle exclusion from copy.")
        self.snapshot_copy_button = ttk.Button(frame, text="Copy to Clipboard", command=self._copy_snapshot_to_clipboard)
        self.snapshot_save_button = ttk.Button(frame, text="Save Map As...", command=self._save_snapshot_as)
        Tooltip(self.snapshot_copy_button, "Copy map (respects ignores).")
        Tooltip(self.snapshot_save_button, "Save map to file.")
        self.snapshot_status_var = tk.StringVar(value="Status: Ready")
        self.snapshot_status_label = ttk.Label(frame, textvariable=self.snapshot_status_var, anchor=tk.W)
        self.snapshot_progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')

    def _create_scaffold_widgets(self):
        frame = self.scaffold_frame
        self.scaffold_input_buttons_frame = ttk.Frame(frame)
        self.scaffold_paste_button = ttk.Button(self.scaffold_input_buttons_frame, text="Paste Map", command=self._paste_map_input)
        self.scaffold_load_button = ttk.Button(self.scaffold_input_buttons_frame, text="Load Map...", command=self._load_map_file)
        self.scaffold_clear_map_button = ttk.Button(self.scaffold_input_buttons_frame, text="Clear Map", command=lambda: self.scaffold_map_input.delete('1.0', tk.END))
        Tooltip(self.scaffold_paste_button, "Paste map from clipboard.")
        Tooltip(self.scaffold_load_button, "Load map from file.")
        Tooltip(self.scaffold_clear_map_button, "Clear map input.")
        self.scaffold_map_input = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=60)
        self.scaffold_map_input.tag_configure(self.TAG_STRIKETHROUGH, overstrike=True, foreground="grey50")
        self.scaffold_map_input.bind("<Button-1>", self._handle_scaffold_map_click)
        Tooltip(self.scaffold_map_input, "Enter map. Click lines to exclude.")
        self.scaffold_config_frame = ttk.Frame(frame)
        self.scaffold_base_dir_label = ttk.Label(self.scaffold_config_frame, text="Base Directory:")
        self.scaffold_base_dir_var = tk.StringVar()
        self.scaffold_base_dir_entry = ttk.Entry(self.scaffold_config_frame, textvariable=self.scaffold_base_dir_var, width=40)
        self.scaffold_browse_base_button = ttk.Button(self.scaffold_config_frame, text="Browse...", command=self._browse_scaffold_base_dir)
        self.scaffold_clear_base_dir_button = ttk.Button(self.scaffold_config_frame, text="X", width=2, command=lambda: self.scaffold_base_dir_var.set(''), style='ClearButton.TButton')
        Tooltip(self.scaffold_browse_base_button, "Select parent directory.")
        Tooltip(self.scaffold_clear_base_dir_button, "Clear base path.")
        self.scaffold_format_label = ttk.Label(self.scaffold_config_frame, text="Input Format:")
        self.scaffold_format_var = tk.StringVar(value="Auto-Detect")
        self.scaffold_format_combo = ttk.Combobox(self.scaffold_config_frame, textvariable=self.scaffold_format_var, values=["Auto-Detect", "Spaces (2)", "Spaces (4)", "Tabs", "Tree", "Generic"], state='readonly', width=15)
        Tooltip(self.scaffold_format_combo, "Map format (Auto-Detect recommended).")
        self.scaffold_create_button = ttk.Button(frame, text="Create Structure", command=self._create_structure)
        Tooltip(self.scaffold_create_button, "Create structure.")
        self.scaffold_status_var = tk.StringVar(value="Status: Ready")
        self.scaffold_status_label = ttk.Label(frame, textvariable=self.scaffold_status_var, anchor=tk.W)
        self.scaffold_open_folder_button = ttk.Button(frame, text="Open Output Folder", command=self._open_last_scaffold_folder)
        self.last_scaffold_path = None
        Tooltip(self.scaffold_open_folder_button, "Open last created folder.")
        self.scaffold_progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=100, mode='determinate')

    # --- Layout Methods ---
    def _layout_snapshot_widgets(self):
        frame = self.snapshot_frame
        frame.columnconfigure(1, weight=1)
        self.snapshot_dir_entry.grid(row=0, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_clear_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 7))
        self.snapshot_browse_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.snapshot_ignore_entry.grid(row=1, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_clear_ignore_button.grid(row=1, column=1, sticky=tk.E, padx=(0, 7))
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5))
        self.snapshot_format_combo.grid(row=3, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_show_emojis_check.grid(row=3, column=2, padx=(0, 10))
        self.snapshot_regenerate_button.grid(row=4, column=0, sticky=tk.W, padx=5, pady=(10, 5))
        self.snapshot_auto_copy_check.grid(row=4, column=1, columnspan=2, sticky=tk.E, padx=15, pady=(10, 5))
        self.snapshot_map_output.grid(row=5, column=0, columnspan=4, sticky=tk.NSEW, padx=5, pady=5) # Span 4
        frame.rowconfigure(5, weight=1)
        self.snapshot_status_label.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=(2, 0))
        self.snapshot_copy_button.grid(row=6, column=2, sticky=tk.E, padx=(0, 5), pady=(2,0))
        self.snapshot_save_button.grid(row=6, column=3, sticky=tk.W, padx=(0, 5), pady=(2,0))
        self.snapshot_progress_bar.grid(row=7, column=0, columnspan=4, sticky=tk.EW, padx=5, pady=(1, 2))
        self.snapshot_progress_bar.grid_remove()

    def _layout_scaffold_widgets(self):
        frame = self.scaffold_frame
        frame.columnconfigure(0, weight=1)
        self.scaffold_input_buttons_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        self.scaffold_paste_button.grid(row=0, column=0, padx=5)
        self.scaffold_load_button.grid(row=0, column=1, padx=5)
        self.scaffold_clear_map_button.grid(row=0, column=2, padx=15)
        self.scaffold_map_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        frame.rowconfigure(1, weight=1)
        self.scaffold_config_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.scaffold_config_frame.columnconfigure(1, weight=1)
        self.scaffold_base_dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.scaffold_base_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.scaffold_clear_base_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 2))
        self.scaffold_browse_base_button.grid(row=0, column=2, sticky=tk.W, padx=(5, 15))
        self.scaffold_format_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 2))
        self.scaffold_format_combo.grid(row=0, column=4, sticky=tk.W, padx=2)
        self.scaffold_create_button.grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=5, padx=5)
        self.scaffold_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(2,0), padx=5)
        self.scaffold_open_folder_button.grid(row=4, column=1, sticky=tk.E, pady=2, padx=5)
        self.scaffold_open_folder_button.grid_remove()
        self.scaffold_progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(1,2))
        self.scaffold_progress_bar.grid_remove()

    # --- Event Handlers / Commands ---
    def _handle_initial_state(self):
        initial_status, active_tab_widget, target_tab_name = "Ready", self.snapshot_frame, self.TAB_SNAPSHOT
        if self.initial_mode == 'snapshot' and self.initial_path:
            target_tab_name, self.snapshot_dir_var.set(str(self.initial_path))
            initial_status = f"Ready: {self.initial_path.name}"
        elif self.initial_mode == 'scaffold_from_file' and self.initial_path:
            active_tab_widget, target_tab_name = self.scaffold_frame, self.TAB_SCAFFOLD
            if self._load_map_from_path(self.initial_path): initial_status, _ = f"Loaded: {self.initial_path.name}", self._check_scaffold_readiness()
            else: initial_status = "Error loading map file."
        elif self.initial_mode == 'scaffold_here' and self.initial_path:
            active_tab_widget, target_tab_name = self.scaffold_frame, self.TAB_SCAFFOLD
            self.scaffold_base_dir_var.set(str(self.initial_path))
            initial_status = f"Base: '{self.initial_path.name}'. Paste map."
            self._check_scaffold_readiness()
        self.notebook.select(active_tab_widget)
        self._update_status(initial_status, tab=target_tab_name)

    def _update_status(self, message, is_error=False, is_success=False, tab=None):
        if tab is None:
            try: tab = self.TAB_SNAPSHOT if self.notebook.index(self.notebook.select()) == 0 else self.TAB_SCAFFOLD
            except tk.TclError: tab = self.TAB_SNAPSHOT
        if isinstance(message, str) and message.lower().startswith("status: "): message = message[len("Status: "):]
        status_var = self.scaffold_status_var if tab == self.TAB_SCAFFOLD else self.snapshot_status_var
        status_label = self.scaffold_status_label if tab == self.TAB_SCAFFOLD else self.snapshot_status_label
        status_var.set(f"Status: {message}")
        try:
            style = ttk.Style(); default_color = style.lookup('TLabel', 'foreground')
            if is_error: color = "red"
            elif is_success: color = "#008000"
            else: color = default_color if default_color else "black"
            status_label.config(foreground=color)
        except tk.TclError: pass # Ignore style/config errors if widget destroyed

    def _check_scaffold_readiness(self):
        try:
            if not all(hasattr(self, w) for w in ['scaffold_map_input', 'scaffold_base_dir_var', 'scaffold_status_var']): return
            map_ok, base_ok = bool(self.scaffold_map_input.get('1.0', tk.END).strip()), bool(self.scaffold_base_dir_var.get())
            status = self.scaffold_status_var.get().lower()
            if map_ok and base_ok and not any(s in status for s in ["ready to create", "error", "processing", "success"]):
                self._update_status("Ready to create structure.", is_success=True, tab=self.TAB_SCAFFOLD)
        except tk.TclError: pass

    def _browse_snapshot_dir(self):
        path = filedialog.askdirectory(mustexist=True, title="Select Source Directory")
        if path: self.snapshot_dir_var.set(path); self._update_status("Source selected.", tab=self.TAB_SNAPSHOT)

    def _copy_snapshot_to_clipboard(self, show_status=True):
        map_widget, tag = self.snapshot_map_output, self.TAG_STRIKETHROUGH
        full_text = map_widget.get('1.0', tk.END).strip()
        ignores = set(p.strip() for p in self.snapshot_ignore_var.get().split(',') if p.strip())
        lines_to_copy, copied = [], False
        try:
            last = map_widget.index('end-1c'); num_lines = int(last.split('.')[0]) if last else 0
            for i in range(1, num_lines + 1):
                start, text = f"{i}.0", map_widget.get(f"{i}.0", f"{i}.end")
                if not text.strip(): continue
                c_start, _ = self._get_content_range(map_widget, start, text)
                struck = tag in map_widget.tag_names(c_start) if c_start else False
                if struck: continue
                item = text.strip().rstrip('/'); ignored = False
                for pattern in ignores:
                     if fnmatch.fnmatch(item, pattern) or (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(item, pattern.rstrip('/\\'))): ignored = True; break
                if ignored: continue
                lines_to_copy.append(text)
        except tk.TclError as e: print(f"ERROR Copy: {e}"); messagebox.showerror("Error", f"Copy prep error:\n{e}"); return False
        final = "\n".join(lines_to_copy)
        msg, err, suc = "", False, False
        if final:
            try: pyperclip.copy(final); copied, suc = True, True; msg = "Map copied (with exclusions)." if len(lines_to_copy) < len(full_text.splitlines()) else "Map copied."
            except Exception as e: msg, err = f"Clipboard error: {e}", True; messagebox.showerror("Clipboard Error", msg)
        else: msg, err = "Nothing valid to copy (all excluded?).", True; messagebox.showwarning("No Content", msg) if show_status else None
        if show_status: self._update_status(msg, is_error=err, is_success=suc, tab=self.TAB_SNAPSHOT)
        return copied

    def _save_snapshot_as(self):
        map_widget = self.snapshot_map_output
        try: text = map_widget.get('1.0', tk.END); txt_strip = text.strip()
        except tk.TclError: messagebox.showerror("Error", "Could not get map text."); return
        if not txt_strip or txt_strip.startswith("Error:"): messagebox.showwarning("No Content", "Nothing valid to save."); return
        fname = "directory_map.txt"
        try: root = txt_strip.splitlines()[0].strip().rstrip('/'); safe = re.sub(r'[<>:"/\\|?*]', '_', root) if root else ""; fname = f"{safe if safe else 'map'}_map.txt"
        except: pass
        path = filedialog.asksaveasfilename(initialfile=fname, defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All", "*.*")], title="Save Map As...")
        if not path: self._update_status("Save cancelled.", tab=self.TAB_SNAPSHOT); return
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(text)
            self._update_status(f"Map saved: {Path(path).name}", is_success=True, tab=self.TAB_SNAPSHOT)
        except Exception as e: messagebox.showerror("Save Error", f"Could not save:\n{e}"); self._update_status("Save failed.", is_error=True, tab=self.TAB_SNAPSHOT)

    def _browse_scaffold_base_dir(self):
        path = filedialog.askdirectory(mustexist=True, title="Select Base Directory")
        if path: self.scaffold_base_dir_var.set(path); self._update_status(f"Base: '{Path(path).name}'.", is_success=True, tab=self.TAB_SCAFFOLD); self._check_scaffold_readiness()

    def _paste_map_input(self):
        try:
            clip = pyperclip.paste()
            if clip: self.scaffold_map_input.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END); self.scaffold_map_input.delete('1.0', tk.END); self.scaffold_map_input.insert('1.0', clip); self._update_status("Pasted map.", is_success=True, tab=self.TAB_SCAFFOLD); self._check_scaffold_readiness()
            else: self._update_status("Clipboard empty.", tab=self.TAB_SCAFFOLD)
        except Exception as e: messagebox.showerror("Clipboard Error", f"Paste failed:\n{e}"); self._update_status("Paste failed.", is_error=True, tab=self.TAB_SCAFFOLD)

    def _load_map_from_path(self, path_obj):
        try:
            with open(path_obj, 'r', encoding='utf-8') as f: content = f.read()
            self.scaffold_map_input.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END); self.scaffold_map_input.delete('1.0', tk.END); self.scaffold_map_input.insert('1.0', content); return True
        except Exception as e: messagebox.showerror("File Load Error", f"Load failed:\n{path_obj.name}\n\n{e}"); return False

    def _load_map_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("Map", "*.map"), ("All", "*.*")], title="Load Map File")
        if path:
            if self._load_map_from_path(Path(path)): self._update_status(f"Loaded: {Path(path).name}", is_success=True, tab=self.TAB_SCAFFOLD); self._check_scaffold_readiness()
            else: self._update_status("Error loading map file.", is_error=True, tab=self.TAB_SCAFFOLD)

    # --- Click Handler Helper Methods ---
    def _get_line_info(self, widget, tk_index):
        try:
            if not widget.get(tk_index).strip() and widget.compare(tk_index, ">=", widget.index(f"{tk_index} lineend")): return None
            start, end = widget.index(f"{tk_index} linestart"), widget.index(f"{tk_index} lineend")
            num, text = int(start.split('.')[0]), widget.get(start, end)
            strip = text.strip(); indent = len(text) - len(text.lstrip()) if strip else 0
            return {"num": num, "start": start, "end": end, "text": text, "stripped": strip, "indent": indent} if strip else None
        except tk.TclError: return None

    def _get_content_range(self, widget, line_start, line_text=None):
        try:
            text = line_text if line_text is not None else widget.get(line_start, f"{line_start} lineend")
            strip = text.strip();
            if not strip: return None, None
            lead = len(text) - len(text.lstrip()); length = len(strip)
            start_idx = f"{line_start} + {lead} chars"; end_idx = f"{start_idx} + {length} chars"
            return start_idx, end_idx
        except tk.TclError: return None, None

    def _toggle_tag_on_range(self, widget, tag, add, start, end):
        if not start or not end: return
        try: widget.tag_add(tag, start, end) if add else widget.tag_remove(tag, start, end)
        except tk.TclError as e: print(f"ERROR tag toggle: {e}")

    def _get_descendant_lines(self, widget, start_num, start_indent):
        desc, num = [], start_num + 1
        while True:
            idx = f"{num}.0";
            if not widget.compare(idx, "<", "end-1c"): break
            text = widget.get(idx, f"{num}.end"); strip = text.strip()
            if not strip: num += 1; continue
            indent = len(text) - len(text.lstrip())
            if indent > start_indent: desc.append((num, idx))
            else: break
            num += 1
        return desc

    def _update_ignore_csv(self, item, add):
        if not item: return False
        var = self.snapshot_ignore_var; current = var.get()
        items = set(p.strip() for p in current.split(',') if p.strip()) if current else set()
        changed = False
        if add:
            if item not in items: items.add(item); changed = True
        else:
            if item in items: items.remove(item); changed = True
        if changed: var.set(", ".join(sorted(list(items))))
        return changed

    def _is_directory_heuristic(self, widget, info):
        if info["stripped"].endswith('/'): return True
        next_num, next_start = info["num"] + 1, f"{info['num'] + 1}.0"
        if widget.compare(next_start, "<", "end-1c"):
            next_text = widget.get(next_start, f"{next_num}.end")
            if next_text.strip(): return (len(next_text) - len(next_text.lstrip())) > info["indent"]
        return False

    # --- UPDATED CLICK HANDLERS ---
    def _handle_snapshot_map_click(self, event):
        """Handles clicks on the snapshot map. Improved stripping & cascade."""
        widget, tag = self.snapshot_map_output, self.TAG_STRIKETHROUGH
        if str(widget.cget("state")) != tk.NORMAL: return

        try:
            info = self._get_line_info(widget, f"@{event.x},{event.y}")
            if not info: return
            c_start, _ = self._get_content_range(widget, info["start"], info["text"])
            if not c_start: return

            apply_tag = tag not in widget.tag_names(c_start)
            descendants = self._get_descendant_lines(widget, info["num"], info["indent"])
            cascade = self._is_directory_heuristic(widget, info) or bool(descendants)
            lines = [(info["num"], info["start"], info["text"])]
            if cascade: lines.extend([(d_num, d_start, widget.get(d_start, f"{d_num}.end")) for d_num, d_start in descendants if widget.get(d_start, f"{d_num}.end").strip()])

            changed = False
            for num, start, text in lines:
                if not text.strip(): continue
                # --- Improved Clean Name Extraction ---
                name = text.lstrip()
                loops, max_loops = 0, 20
                while loops < max_loops:
                    start_len = len(name)
                    if name.startswith(TREE_PIPE): name = name[len(TREE_PIPE):]
                    elif name.startswith(TREE_SPACE): name = name[len(TREE_SPACE):]
                    elif name.startswith(TREE_BRANCH): name = name[len(TREE_BRANCH):]
                    elif name.startswith(TREE_LAST_BRANCH): name = name[len(TREE_LAST_BRANCH):]
                    name = name.lstrip(' ') # Strip extra space
                    if len(name) == start_len: break
                    loops += 1
                for emoji in ALL_KNOWN_EMOJIS_FOR_STRIPPING:
                    if name.startswith(emoji):
                        name = name[len(emoji):]
                        if name.startswith(' '): name = name[1:]
                        break
                clean_name = name.rstrip('/').strip()
                # --- End Extraction ---

                if not clean_name: print(f"Warn: No clean name line {num}: '{text.rstrip()}'"); continue

                cs, ce = self._get_content_range(widget, start, text)
                self._toggle_tag_on_range(widget, tag, apply_tag, cs, ce)
                if self._update_ignore_csv(clean_name, apply_tag): changed = True

            if changed:
                action = "Added" if apply_tag else "Removed"
                self._update_status(f"{action} item(s) to custom ignores.", tab=self.TAB_SNAPSHOT)
                if self.snapshot_auto_copy_var.get(): self._copy_snapshot_to_clipboard(show_status=False)

        except Exception as e: print(f"ERROR snapshot click: {e}"); import traceback; traceback.print_exc()

    def _handle_scaffold_map_click(self, event):
        """Handles clicks on the scaffold map input area."""
        widget, tag = self.scaffold_map_input, self.TAG_STRIKETHROUGH
        if str(widget.cget("state")) != tk.NORMAL: return

        try:
            info = self._get_line_info(widget, f"@{event.x},{event.y}")
            if not info: return
            c_start, _ = self._get_content_range(widget, info["start"], info["text"])
            if not c_start: return

            apply_tag = tag not in widget.tag_names(c_start)
            descendants = self._get_descendant_lines(widget, info["num"], info["indent"])
            lines = [(info["num"], info["start"], info["text"])]
            lines.extend([(d_num, d_start, widget.get(d_start, f"{d_num}.end")) for d_num, d_start in descendants if widget.get(d_start, f"{d_num}.end").strip()])

            for num, start, text in lines:
                cs, ce = self._get_content_range(widget, start, text)
                self._toggle_tag_on_range(widget, tag, apply_tag, cs, ce)
        except Exception as e: print(f"ERROR scaffold click: {e}"); import traceback; traceback.print_exc()

    # --- Threading / Queue Helpers ---
    def _start_background_task(self, target_func, args, queue_obj, button, progressbar, status_msg, tab, progress_mode, check_func):
        try: button.config(state=tk.DISABLED)
        except tk.TclError: print("Warn: Button disable failed."); return # Stop if button gone
        if progressbar and progressbar.winfo_exists():
            progressbar['value'], progressbar['mode'] = 0, progress_mode
            progressbar.grid();
            if progress_mode == 'indeterminate': progressbar.start()
            self.update_idletasks()
        self._update_status(status_msg, tab=tab)
        thread_attr = "snapshot_thread" if tab == self.TAB_SNAPSHOT else "scaffold_thread"
        thread = threading.Thread(target=target_func, args=args + (queue_obj,), daemon=True)
        setattr(self, thread_attr, thread); thread.start()
        if check_func: self.after(100, check_func)
        else: print(f"Warn: No queue check func for {tab}."); self._finalize_task_ui(button, progressbar) # Reset if no check

    def _finalize_task_ui(self, button, progressbar):
        try:
            if progressbar and progressbar.winfo_exists(): progressbar.stop(); progressbar.grid_remove()
            if button and button.winfo_exists(): button.config(state=tk.NORMAL)
        except tk.TclError: print("Warn: Finalize UI error (widget destroyed?).")

    # --- UPDATED Trigger Methods ---
    def _generate_snapshot(self):
        src = self.snapshot_dir_var.get()
        if not src or not Path(src).is_dir(): messagebox.showwarning("Input Required", "Select valid source directory."); return
        ignores_str = self.snapshot_ignore_var.get()
        ignores = set(p.strip() for p in ignores_str.split(',') if p.strip()) if ignores_str else None
        fmt, emojis = self.snapshot_format_var.get(), self.snapshot_show_emojis_var.get()
        try: self.snapshot_map_output.config(state=tk.NORMAL); self.snapshot_map_output.delete('1.0', tk.END); self.snapshot_map_output.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)
        except tk.TclError: print("Warn: Map output clear failed."); return # Stop if widget gone
        self._start_background_task(self._snapshot_thread_target, (src, ignores, self.user_default_ignores, fmt, emojis), self.snapshot_queue, self.snapshot_regenerate_button, self.snapshot_progress_bar, "Generating map...", self.TAB_SNAPSHOT, 'indeterminate', self._check_snapshot_queue)

    def _create_structure(self):
        """Handles 'Create Structure'. Expands exclusions before calling backend."""
        map_widget, tag = self.scaffold_map_input, self.TAG_STRIKETHROUGH
        map_text, base_dir, fmt_hint = map_widget.get('1.0', tk.END).strip(), self.scaffold_base_dir_var.get(), self.scaffold_format_var.get()
        if not map_text: messagebox.showwarning("Input Required", "Map input empty."); return
        if not base_dir or not Path(base_dir).is_dir(): messagebox.showwarning("Input Required", "Select valid base directory."); return

        initial_excludes = set()
        try: # Get initially excluded lines from UI tags
            last = map_widget.index('end-1c'); num_lines = int(last.split('.')[0]) if last else 0
            for i in range(1, num_lines + 1):
                start = f"{i}.0"; c_start, _ = self._get_content_range(map_widget, start)
                if c_start and tag in map_widget.tag_names(c_start): initial_excludes.add(i)
        except tk.TclError as e: print(f"ERROR reading tags: {e}"); messagebox.showerror("Error", f"Exclusion error:\n{e}"); return

        # --- Expand Exclusions ---
        final_excludes = set(initial_excludes)
        try:
            # Use logic module to parse (can fail if logic not imported)
            if logic:
                 parsed = logic.parse_map(map_text, fmt_hint, excluded_lines=set())
                 if parsed:
                      line_map = {}; idx = 0; lines = map_text.splitlines()
                      for i, line in enumerate(lines):
                           ln = i + 1
                           if line.strip() and not line.strip().startswith('#'):
                                if idx < len(parsed): line_map[ln] = idx; idx += 1
                      parents_to_check = list(initial_excludes); processed = set()
                      while parents_to_check:
                           p_ln = parents_to_check.pop(0)
                           if p_ln in processed: continue; processed.add(p_ln)
                           p_idx = line_map.get(p_ln)
                           if p_idx is not None:
                                p_lvl, _, p_is_dir = parsed[p_idx]
                                if p_is_dir:
                                     c_ln = p_ln + 1
                                     while c_ln <= len(lines):
                                          c_idx = line_map.get(c_ln)
                                          if c_idx is not None:
                                               c_lvl, _, _ = parsed[c_idx]
                                               if c_lvl > p_lvl:
                                                    if c_ln not in final_excludes: final_excludes.add(c_ln); parents_to_check.append(c_ln)
                                               elif c_lvl <= p_lvl: break
                                          elif not lines[c_ln-1].strip(): pass
                                          else: break # Stop if line not parsed
                                          c_ln += 1
                 else: print("Warn: Map pre-parsing failed for exclusion expansion.")
            else: print("Warn: Logic module not available for exclusion expansion.")
        except Exception as e: print(f"ERROR expanding excludes: {e}"); import traceback; traceback.print_exc(); final_excludes = set(initial_excludes)
        # --- End Expand Exclusions ---

        self.scaffold_open_folder_button.grid_remove(); self.last_scaffold_path = None
        print(f"Starting scaffold, final excludes: {sorted(list(final_excludes))}")
        self._start_background_task(self._scaffold_thread_target, (map_text, base_dir, fmt_hint, final_excludes), self.scaffold_queue, self.scaffold_create_button, self.scaffold_progress_bar, "Processing...", self.TAB_SCAFFOLD, 'determinate', self._check_scaffold_queue)
        try: # Set progress bar max
            if hasattr(self, 'scaffold_progress_bar') and self.scaffold_progress_bar.winfo_exists():
                 total = max(1, len(map_text.splitlines()) - len(final_excludes))
                 self.scaffold_progress_bar['maximum'] = total
        except tk.TclError: pass

    # --- Thread Target Functions ---
    def _snapshot_thread_target(self, src, cust_ign, user_ign, fmt, emojis, q):
        try: res = logic.create_directory_snapshot(src, cust_ign, user_ign, fmt, emojis); q.put({'type': self.QUEUE_MSG_RESULT, 'success': not res.startswith("Error:"), 'map_text': res})
        except Exception as e: q.put({'type': self.QUEUE_MSG_RESULT, 'success': False, 'map_text': f"Thread Error: {e}"}); print(f"Snap thread ERR: {e}")

    def _scaffold_thread_target(self, map_txt, base, hint, excludes, q):
        root = None
        try: msg, suc, root = logic.create_structure_from_map(map_txt, base, hint, excludes, q); q.put({'type': self.QUEUE_MSG_RESULT, 'success': suc, 'message': msg, 'root_name': root})
        except Exception as e: q.put({'type': self.QUEUE_MSG_RESULT, 'success': False, 'message': f"Thread Error: {e}", 'root_name': None}); print(f"Scaf thread ERR: {e}"); import traceback; traceback.print_exc()

    # --- Queue Checking Functions ---
    def _check_snapshot_queue(self):
        try:
            while True:
                msg = self.snapshot_queue.get_nowait(); mtype = msg.get('type')
                if mtype == self.QUEUE_MSG_RESULT:
                    suc, txt = msg['success'], msg['map_text']
                    try: # Update widget safely
                        if self.snapshot_map_output.winfo_exists(): self.snapshot_map_output.config(state=tk.NORMAL); self.snapshot_map_output.delete('1.0', tk.END); self.snapshot_map_output.insert('1.0', txt); self.snapshot_map_output.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)
                    except tk.TclError: pass
                    status = "Generated." if suc else txt
                    if suc and self.snapshot_auto_copy_var.get(): copied = self._copy_snapshot_to_clipboard(show_status=False); status = "Generated & Copied." if copied else "Generated (copy failed)."
                    self._update_status(status, is_error=not suc, is_success=suc, tab=self.TAB_SNAPSHOT)
                    self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar)
                    return
        except queue.Empty:
            thread = getattr(self, 'snapshot_thread', None)
            if thread and thread.is_alive(): self.after(100, self._check_snapshot_queue)
            else: self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar) # Finalize if thread done/missing
        except Exception as e: print(f"ERROR check snap Q: {e}"); import traceback; traceback.print_exc(); self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar)

    def _check_scaffold_queue(self):
        try:
            while True:
                msg = self.scaffold_queue.get_nowait(); mtype = msg.get('type')
                if mtype == self.QUEUE_MSG_PROGRESS:
                    curr, tot = msg.get('current', 0), msg.get('total', 1)
                    try: # Update progress bar safely
                        pb = self.scaffold_progress_bar
                        if pb and pb.winfo_exists(): pbmax = max(1, tot); pb['maximum'] = pbmax; pb['mode'] = 'determinate'; pb['value'] = curr
                    except Exception as e: print(f"Warn: Prog bar update error: {e}")
                elif mtype == self.QUEUE_MSG_RESULT:
                    suc, txt, root = msg.get('success', False), msg.get('message', 'Unknown'), msg.get('root_name')
                    self._update_status(txt, is_error=not suc, is_success=suc, tab=self.TAB_SCAFFOLD)
                    self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)
                    if suc and root: self._show_open_folder_button(root)
                    return
        except queue.Empty:
            thread = getattr(self, 'scaffold_thread', None)
            if thread and thread.is_alive(): self.after(100, self._check_scaffold_queue)
            else: self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)
        except Exception as e: print(f"ERROR check scaf Q: {e}"); import traceback; traceback.print_exc(); self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)

    def _show_open_folder_button(self, root_name):
         try:
              base = self.scaffold_base_dir_var.get()
              btn = self.scaffold_open_folder_button
              if not base or not root_name or not btn or not btn.winfo_exists(): self.last_scaffold_path = None; btn.grid_remove(); return
              path = Path(base) / root_name
              if path.is_dir(): self.last_scaffold_path = path; btn.grid()
              else: print(f"Warn: Path check failed: {path}"); self.last_scaffold_path = None; btn.grid_remove()
         except Exception as e: print(f"Warn: Show open btn error: {e}"); self.last_scaffold_path = None; self.scaffold_open_folder_button.grid_remove()

    def _open_last_scaffold_folder(self):
        path = self.last_scaffold_path
        if not path or not path.is_dir(): self._update_status("Output folder not found/recorded.", is_error=True, tab=self.TAB_SCAFFOLD); return
        path_str = str(path)
        try:
            print(f"Info: Opening: {path_str}")
            if sys.platform == "win32": os.startfile(path_str)
            elif sys.platform == "darwin": subprocess.run(['open', path_str], check=True)
            else: subprocess.run(['xdg-open', path_str], check=True)
            self._update_status(f"Opened: {path.name}", is_success=True, tab=self.TAB_SCAFFOLD)
        except Exception as e: messagebox.showerror("Error", f"Could not open '{path.name}':\n{e}"); self._update_status("Open failed.", is_error=True, tab=self.TAB_SCAFFOLD)

    # --- Help Menu Methods ---
    def _show_about(self):
        messagebox.showinfo("About DirSnap", f"DirSnap {APP_VERSION}\n\nMap & Scaffold Directories.\nAsa V. Schaeffer & Google")

    def _view_readme(self):
        try:
            pdir = Path(__file__).parent.parent; readme = pdir / "README.md"; cwd_readme = Path.cwd() / "README.md"
            path = readme if readme.is_file() else cwd_readme if cwd_readme.is_file() else None
            if not path: messagebox.showwarning("Not Found", "README.md not found."); return
            path_str = str(path.resolve()); print(f"Info: Opening README: {path_str}")
            if sys.platform == "win32": os.startfile(path_str)
            elif sys.platform == "darwin": subprocess.run(['open', path_str], check=True)
            else: subprocess.run(['xdg-open', path_str], check=True)
        except Exception as e: messagebox.showerror("Error", f"Could not open README:\n{e}")

# --- Main execution block ---
if __name__ == '__main__':
    print("Running app.py directly...")
    # Example: Test scaffold_here mode
    # test_path = str(Path('./_ui_test').resolve()); Path(test_path).mkdir(exist_ok=True)
    # app = DirSnapApp(initial_path=test_path, initial_mode='scaffold_here')
    app = DirSnapApp() # Run normally for testing
    app.mainloop()
    # Cleanup if needed: if Path(test_path).exists(): shutil.rmtree(test_path)