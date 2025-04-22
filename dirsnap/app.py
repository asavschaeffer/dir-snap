# dirsnap/app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkFont # Import font submodule
import pyperclip # Dependency: pip install pyperclip
import json
from pathlib import Path
import sys
import os
import subprocess
import fnmatch
import shutil
import re
import threading
import queue
import time # Keep for potential future debug/sleep

# Use relative import to access logic.py within the same package
try:
    from . import logic
    from .utils import get_config_path
except ImportError:
    # Fallback for running app.py directly for testing UI (not recommended for final)
    print("Warning: Running app.py directly. Attempting to import logic module from current directory.")
    import logic
    # Attempt to import utils directly if running standalone
    try:
        from utils import get_config_path
    except ImportError:
        print("ERROR: Could not import get_config_path. Config loading/saving will fail.")
        # Define a dummy function to avoid NameError later, but show error
        def get_config_path():
            print("FATAL: get_config_path is not available.")
            return None # Or raise an exception
        
# --- Application Constants ---
APP_VERSION = "3.1.0" # Example version

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
        self.widget.bind("<Enter>", self.schedule_tooltip, add='+') # Use add='+'' to avoid replacing other bindings
        self.widget.bind("<Leave>", self.hide_tooltip, add='+')
        self.widget.bind("<ButtonPress>", self.hide_tooltip, add='+')
        self.tip_window = None
        self.id = None

    def schedule_tooltip(self, event=None):
        """Schedules the tooltip to appear after a delay."""
        self.hide_tooltip()
        self.id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self, event=None):
        """Displays the tooltip window."""
        if self.tip_window or not self.text:
            return

        # Position near cursor
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True) # Keep window borderless
        self.tip_window.wm_geometry(f"+{x}+{y}") # Position near cursor

        label = tk.Label(self.tip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength=self.wraplength, padx=4, pady=2)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        """Hides the tooltip window."""
        scheduled_id = self.id
        self.id = None
        if scheduled_id:
            try:
                self.widget.after_cancel(scheduled_id)
            except ValueError: # Handle case where 'after' job might already be invalid
                pass

        tip = self.tip_window
        self.tip_window = None
        if tip:
            try:
                tip.destroy()
            except tk.TclError: # Handle case where window might already be destroyed
                pass

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
        self.user_default_ignores = [] # To store ignores loaded from config
        self.last_scaffold_path = None # Already exists

        # Queues for inter-thread communication
        self.scaffold_queue = queue.Queue()
        self.snapshot_queue = queue.Queue()

        # Store thread objects to check if they are alive
        self.scaffold_thread = None
        self.snapshot_thread = None

        self.initial_path = Path(initial_path) if initial_path else None
        self.initial_mode = initial_mode

        self.title("Directory Mapper & Scaffolder")
        self.minsize(550, 450)

         # --- Create Menu Bar --- 
        self.menu_bar = tk.Menu(self)

        # --- File Menu ---
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        # Add other file-related commands here later if needed (e.g., New Window?)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_closing)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu) # Add File menu to bar

        # --- Edit Menu ---
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="Preferences...", command=self._open_config_file) # Renamed, linked to same function
        # Add other edit commands later if needed (e.g., Copy, Paste for text areas?)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu) # Add Edit menu to bar
        
        # --- Help Menu ---
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="View README", command=self._view_readme)
        self.help_menu.add_command(label="About DirSnap", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        
        # Configure the root window to use the menu bar
        self.config(menu=self.menu_bar)

        self._configure_styles() # Configure styles in a helper method

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

        self._load_config()

        # --- Layout Widgets ---
        self._layout_snapshot_widgets()
        self._layout_scaffold_widgets()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Handle initial state after UI is drawn
        self.after(50, self._handle_initial_state)

    def _configure_styles(self):
        """Configure custom ttk styles."""
        style = ttk.Style(self)
        try:
            text_color = style.lookup('TLabel', 'foreground')
        except tk.TclError:
            print("Warning: Could not look up theme colors for style config, using fallback.")
            text_color = 'black'

        # Style for clear buttons in Entries
        style.configure('ClearButton.TButton',
                        foreground='grey',
                        borderwidth=0,
                        relief='flat',
                        padding=0
                       )
        style.map('ClearButton.TButton',
                  foreground=[('active', text_color), ('pressed', text_color)]
                  )

# --- Configuration Methods ---

    def _load_config(self):
            """Loads settings from the configuration file."""
            config_path = get_config_path()
            if not config_path or not config_path.exists():
                print("Info: Configuration file not found. Using default settings.")
                # Apply default window size if needed (optional)
                # self.geometry("550x450") # Example default size
                return # Nothing to load

            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error: Failed to load or parse config file '{config_path}': {e}")
                messagebox.showwarning("Config Load Error",
                                    f"Could not load configuration file.\nUsing default settings.\n\nError: {e}",
                                    parent=self) # Show parent to appear over main window
                # Apply default window size if needed (optional)
                # self.geometry("550x450") # Example default size
                return

            # Apply settings safely using .get() with defaults
            # Window Geometry
            window_conf = config_data.get("window", {})
            width = window_conf.get("width", 550)
            height = window_conf.get("height", 450)
            x_pos = window_conf.get("x_pos")
            y_pos = window_conf.get("y_pos")
            if x_pos is not None and y_pos is not None:
                self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
            else:
                self.geometry(f"{width}x{height}") # Default position

            # Snapshot Settings
            snapshot_conf = config_data.get("snapshot", {})
            last_source = snapshot_conf.get("last_source_dir")
            # Only set if not launched with a specific path context
            if last_source and not self.initial_path:
                self.snapshot_dir_var.set(last_source)

            self.snapshot_auto_copy_var.set(snapshot_conf.get("auto_copy", False))
            # Optional: Load last session's custom ignores
            # last_custom_ignores = snapshot_conf.get("last_custom_ignores", "")
            # self.snapshot_ignore_var.set(last_custom_ignores) # Uncomment if desired

            # Scaffold Settings
            scaffold_conf = config_data.get("scaffold", {})
            last_base = scaffold_conf.get("last_base_dir")
            # Only set if not launched with a specific path context for scaffold_here
            if last_base and not (self.initial_path and self.initial_mode == 'scaffold_here'):
                self.scaffold_base_dir_var.set(last_base)

            self.scaffold_format_var.set(scaffold_conf.get("last_format", "Auto-Detect"))

            # User Default Ignores (Store them for use in logic.py later)
            loaded_ignores = config_data.get("user_default_ignores", [])
            if isinstance(loaded_ignores, list):
                self.user_default_ignores = loaded_ignores
            else:
                print(f"Warning: 'user_default_ignores' in config is not a list. Ignoring. Value: {loaded_ignores}")
                self.user_default_ignores = [] # Reset to default empty list

            print(f"Info: Configuration loaded successfully from {config_path}")
            # Optional: Update the snapshot default ignores label/tooltip here if desired
            # self._update_snapshot_ignores_display() # Example call to a new method

    def _save_config(self):
        """Saves current settings to the configuration file."""
        config_path = get_config_path()
        if not config_path:
             print("Error: Could not determine config path. Settings not saved.")
             return

        settings = {
            "version": 1, # Increment if structure changes significantly later
            "window": {},
            "snapshot": {},
            "scaffold": {},
            "user_default_ignores": self.user_default_ignores # Assumes this list is managed somehow
        }

        # Get Window Geometry
        try:
             # Parse geometry string like "600x500+100+100"
             geo_string = self.geometry()
             parts = geo_string.split('+')
             size_parts = parts[0].split('x')
             settings["window"]["width"] = int(size_parts[0])
             settings["window"]["height"] = int(size_parts[1])
             # Check if position is included
             if len(parts) == 3:
                  settings["window"]["x_pos"] = int(parts[1])
                  settings["window"]["y_pos"] = int(parts[2])
             else: # Handle case where window might be unmapped or position unavailable
                 settings["window"]["x_pos"] = None # Or store previous valid position
                 settings["window"]["y_pos"] = None
        except (tk.TclError, ValueError, IndexError) as e:
             print(f"Warning: Could not get or parse window geometry: {e}. Size/position not saved.")
             # Use potentially loaded values or defaults if parsing fails
             settings["window"] = self._load_config().get("window", {"width": 550, "height": 450}) # Example fallback


        # Get Settings from UI Variables
        settings["snapshot"]["last_source_dir"] = self.snapshot_dir_var.get()
        settings["snapshot"]["auto_copy"] = self.snapshot_auto_copy_var.get()
        # Optional: Save last session's custom ignores
        # settings["snapshot"]["last_custom_ignores"] = self.snapshot_ignore_var.get()

        settings["scaffold"]["last_base_dir"] = self.scaffold_base_dir_var.get()
        settings["scaffold"]["last_format"] = self.scaffold_format_var.get()

        # Write to file
        try:
             # Ensure directory exists (get_config_path should have done this, but double-check)
             config_path.parent.mkdir(parents=True, exist_ok=True)
             with open(config_path, 'w', encoding='utf-8') as f:
                  json.dump(settings, f, indent=4) # Use indent for readability
             print(f"Info: Configuration saved successfully to {config_path}")
        except (OSError, TypeError) as e:
             print(f"Error: Failed to save config file '{config_path}': {e}")
             # Optionally show a messagebox, but maybe annoying on close
             # messagebox.showerror("Config Save Error",
             #                     f"Could not save configuration file.\n\nError: {e}",
             #                     parent=self)

    def _on_closing(self):
        """Handles window closing: saves config and exits."""
        print("Info: Closing application, saving configuration...")
        self._save_config()
        self.destroy() # Close the Tkinter window/application

    def _open_config_file(self):
        """Opens the config.json file in the default system editor."""
        config_path = get_config_path() # From utils.py
        if not config_path:
            messagebox.showerror("Error", "Could not determine the configuration file path.", parent=self)
            return

        if not config_path.is_file():
            # Offer to create it by saving current defaults?
            if messagebox.askyesno("Config File Not Found",
                                   f"The configuration file does not exist yet:\n{config_path}\n\n"
                                   "Do you want to create it now with default settings?",
                                   parent=self):
                self._save_config() # Save current (likely default) settings
                # Check again if save was successful
                if not config_path.is_file():
                     messagebox.showerror("Error", f"Failed to create configuration file:\n{config_path}", parent=self)
                     return
            else:
                 return # User chose not to create it

        # Open the file using platform-specific methods
        path_str = str(config_path)
        try:
            print(f"Info: Attempting to open config file: {path_str}")
            if sys.platform == "win32":
                os.startfile(path_str)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', path_str], check=True)
            else: # Linux and other POSIX variants
                # Use xdg-open for better desktop environment integration
                subprocess.run(['xdg-open', path_str], check=True)
            # Optional: Add status update? Maybe not necessary for opening a file.
        except FileNotFoundError:
             err_msg = f"Could not find the command (e.g., 'open' or 'xdg-open') needed to open the file on this system ({sys.platform})."
             messagebox.showerror("Error Opening File", err_msg, parent=self)
        except subprocess.CalledProcessError as e:
              err_msg = f"The command to open the file failed:\n{e}"
              messagebox.showerror("Error Opening File", err_msg, parent=self)
        except Exception as e:
            err_msg = f"An unexpected error occurred while trying to open the file:\n{config_path}\n\n{e}"
            messagebox.showerror("Error Opening File", err_msg, parent=self)

    # --- Widget Creation Methods ---

    def _create_snapshot_widgets(self):
        """Creates widgets for the Snapshot tab."""
        frame = self.snapshot_frame # Use local variable for clarity

        # Labels
        ttk.Label(frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Label(frame, text="Custom Ignores (comma-sep):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)

        # Default Ignores Label
        try:
            common_defaults = sorted(list(logic.DEFAULT_IGNORE_PATTERNS))[:4]
            default_ignores_text = f"Ignoring defaults like: {', '.join(common_defaults)}, ..."
            default_tooltip = "Also ignoring:\n" + "\n".join(sorted(list(logic.DEFAULT_IGNORE_PATTERNS)))
        except AttributeError: # Handle case where logic might not be imported correctly
             common_defaults = ["N/A"]
             default_ignores_text = "Ignoring default patterns..."
             default_tooltip = "Default ignore patterns unavailable."

        self.snapshot_default_ignores_label = ttk.Label(frame, text=default_ignores_text, foreground="grey")
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5))
        Tooltip(self.snapshot_default_ignores_label, default_tooltip)

        # Entries & Buttons
        self.snapshot_dir_var = tk.StringVar()
        self.snapshot_dir_entry = ttk.Entry(frame, textvariable=self.snapshot_dir_var, width=50)
        self.snapshot_browse_button = ttk.Button(frame, text="Browse...", command=self._browse_snapshot_dir)
        self.snapshot_clear_dir_button = ttk.Button(frame, text="X", width=2, command=lambda: self.snapshot_dir_var.set(''), style='ClearButton.TButton')
        Tooltip(self.snapshot_browse_button, "Select the root directory to generate a map for.")
        Tooltip(self.snapshot_clear_dir_button, "Clear directory path")

        self.snapshot_ignore_var = tk.StringVar()
        self.snapshot_ignore_entry = ttk.Entry(frame, textvariable=self.snapshot_ignore_var, width=50)
        self.snapshot_clear_ignore_button = ttk.Button(frame, text="X", width=2, command=lambda: self.snapshot_ignore_var.set(''), style='ClearButton.TButton')
        Tooltip(self.snapshot_ignore_entry, "Enter comma-separated names/patterns to ignore (e.g., .git, *.log, temp/)")
        Tooltip(self.snapshot_clear_ignore_button, "Clear custom ignores")

        # --- Snapshot Format Widgets --- 
        ttk.Label(frame, text="Output Format:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3) # Grid positioning done here

        self.snapshot_format_var = tk.StringVar(value="Standard Indent") # Default value
        self.snapshot_format_options = ["Standard Indent", "Tree", "Tabs"] # Define options
        self.snapshot_format_combo = ttk.Combobox(
            frame, textvariable=self.snapshot_format_var,
            values=self.snapshot_format_options,
            state='readonly', width=18 # Adjusted width
        )
        Tooltip(self.snapshot_format_combo, "Select the output format for the snapshot map.")

        self.snapshot_show_emojis_var = tk.BooleanVar(value=False) # Default value
        self.snapshot_show_emojis_check = ttk.Checkbutton(
            frame, text="Emojis 📁📄", variable=self.snapshot_show_emojis_var
        )
        Tooltip(self.snapshot_show_emojis_check, "If checked, prepend folder/file emojis to items in the map.")

        self.snapshot_regenerate_button = ttk.Button(frame, text="Generate / Regenerate Map", command=self._generate_snapshot)
        Tooltip(self.snapshot_regenerate_button, "Generate/Refresh the directory map based on current settings.")

        # Checkbox
        self.snapshot_auto_copy_var = tk.BooleanVar(value=False)
        self.snapshot_auto_copy_check = ttk.Checkbutton(frame, text="Auto-copy on generation/click", variable=self.snapshot_auto_copy_var)
        Tooltip(self.snapshot_auto_copy_check, "If checked, automatically copy the map to clipboard upon generation or click-to-exclude.")

        # Output Area
        self.snapshot_map_output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED)
        self.snapshot_map_output.tag_configure(self.TAG_STRIKETHROUGH, overstrike=True, foreground="grey50")
        self.snapshot_map_output.bind("<Button-1>", self._handle_snapshot_map_click)
        Tooltip(self.snapshot_map_output, "Click on a line to toggle exclusion from copy.")

        # Action Buttons
        self.snapshot_copy_button = ttk.Button(frame, text="Copy to Clipboard", command=self._copy_snapshot_to_clipboard)
        self.snapshot_save_button = ttk.Button(frame, text="Save Map As...", command=self._save_snapshot_as)
        Tooltip(self.snapshot_copy_button, "Copy the generated map text (respecting exclusions) to the clipboard.")
        Tooltip(self.snapshot_save_button, "Save the generated map text to a file.")

        # Snapshot Status
        self.snapshot_status_var = tk.StringVar(value="Status: Ready")
        self.snapshot_status_label = ttk.Label(frame, textvariable=self.snapshot_status_var, anchor=tk.W)

        # Snapshot Progress Bar
        self.snapshot_progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')

    def _create_scaffold_widgets(self):
        """Creates widgets for the Scaffold tab."""
        frame = self.scaffold_frame # Use local variable

        # Input Area & Buttons
        self.scaffold_input_buttons_frame = ttk.Frame(frame) # Local frame for buttons
        self.scaffold_paste_button = ttk.Button(self.scaffold_input_buttons_frame, text="Paste Map", command=self._paste_map_input)
        self.scaffold_load_button = ttk.Button(self.scaffold_input_buttons_frame, text="Load Map...", command=self._load_map_file)
        self.scaffold_clear_map_button = ttk.Button(self.scaffold_input_buttons_frame, text="Clear Map", command=lambda: self.scaffold_map_input.delete('1.0', tk.END))
        Tooltip(self.scaffold_paste_button, "Paste map text from clipboard into the input area.")
        Tooltip(self.scaffold_load_button, "Load map text from a file into the input area.")
        Tooltip(self.scaffold_clear_map_button, "Clear the map input area.")

        self.scaffold_map_input = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=60)
        self.scaffold_map_input.tag_configure(self.TAG_STRIKETHROUGH, overstrike=True, foreground="grey50")
        self.scaffold_map_input.bind("<Button-1>", self._handle_scaffold_map_click)
        Tooltip(self.scaffold_map_input, "Enter or paste your directory map here.\nClick lines to toggle exclusion from creation.")

        # Config Row Frame
        self.scaffold_config_frame = ttk.Frame(frame) # Local frame for config
        self.scaffold_base_dir_label = ttk.Label(self.scaffold_config_frame, text="Base Directory:")
        self.scaffold_base_dir_var = tk.StringVar()
        self.scaffold_base_dir_entry = ttk.Entry(self.scaffold_config_frame, textvariable=self.scaffold_base_dir_var, width=40)
        self.scaffold_browse_base_button = ttk.Button(self.scaffold_config_frame, text="Browse...", command=self._browse_scaffold_base_dir)
        self.scaffold_clear_base_dir_button = ttk.Button(self.scaffold_config_frame, text="X", width=2, command=lambda: self.scaffold_base_dir_var.set(''), style='ClearButton.TButton')
        Tooltip(self.scaffold_browse_base_button, "Select the existing parent directory where the new structure will be created.")
        Tooltip(self.scaffold_clear_base_dir_button, "Clear base directory path")

        self.scaffold_format_label = ttk.Label(self.scaffold_config_frame, text="Input Format:")
        self.scaffold_format_var = tk.StringVar(value="Auto-Detect")
        self.scaffold_format_combo = ttk.Combobox(
            self.scaffold_config_frame, textvariable=self.scaffold_format_var,
            values=["Auto-Detect", "Spaces (2)", "Spaces (4)", "Tabs", "Tree", "Generic"],
            state='readonly', width=15 # Adjusted width slightly
        )
        Tooltip(self.scaffold_format_combo, "Select the expected format of the input map (Auto-Detect recommended).")

        # Action Button
        self.scaffold_create_button = ttk.Button(frame, text="Create Structure", command=self._create_structure)
        Tooltip(self.scaffold_create_button, "Create the directory structure defined in the map input within the selected base directory.")

        # Status Bar
        self.scaffold_status_var = tk.StringVar(value="Status: Ready")
        self.scaffold_status_label = ttk.Label(frame, textvariable=self.scaffold_status_var, anchor=tk.W)

        # Open Folder Button
        self.scaffold_open_folder_button = ttk.Button(frame, text="Open Output Folder", command=self._open_last_scaffold_folder)
        self.last_scaffold_path = None
        Tooltip(self.scaffold_open_folder_button, "Open the folder created by the last successful scaffold operation.")

        # Scaffold Progress Bar
        self.scaffold_progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=100, mode='determinate')

    # --- Layout Methods ---

# Inside DirSnapApp class in DirSnap/app.py

    def _layout_snapshot_widgets(self):
        """Arranges widgets in the Snapshot tab using grid (REVISED LAYOUT v3)."""
        frame = self.snapshot_frame

        # --- Configure Grid Columns ---
        # 0: Labels
        # 1: Main Entry Fields / Controls (Expandable)
        # 2: Browse Button / Right-aligned controls
        frame.columnconfigure(1, weight=1) # Allow column 1 (entries) to expand

        # --- Row 0: Source Directory ---
        # Label created and gridded in _create_snapshot_widgets (assuming row=0, col=0, sticky=W)
        self.snapshot_dir_entry.grid(row=0, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_clear_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 7)) # Overlay on entry
        self.snapshot_browse_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)

        # --- Row 1: Custom Ignores ---
        # Label created and gridded in _create_snapshot_widgets (assuming row=1, col=0, sticky=W)
        self.snapshot_ignore_entry.grid(row=1, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_clear_ignore_button.grid(row=1, column=1, sticky=tk.E, padx=(0, 7)) # Overlay on entry

        # --- Row 2: Default Ignores Info ---
        # Label created and gridded in _create_snapshot_widgets (assuming row=2, col=1, columnspan=2, sticky=W)
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5))

        # --- Row 3: Format Options ---
        self.snapshot_format_combo.grid(row=3, column=1, sticky=tk.EW, pady=3, padx=(0, 5))
        self.snapshot_show_emojis_check.grid(row=3, column=2, padx=(0, 10))

        # --- Row 4: Action Row ---
        # Place buttons directly, maybe spanning columns is easier to manage
        self.snapshot_regenerate_button.grid(row=4, column=0, sticky=tk.W, padx=5, pady=(10, 5))
        self.snapshot_auto_copy_check.grid(row=4, column=1, columnspan=2, sticky=tk.E, padx=15, pady=(10, 5)) # Align right, span cols 1 & 2

        # --- Row 5: Output Area ---
        self.snapshot_map_output.grid(row=5, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=5) # Span all 3 columns
        frame.rowconfigure(5, weight=1) # Allow this row to expand vertically

        # --- Row 6: Bottom Bar (Status + Buttons) ---
        # Place status label directly
        self.snapshot_status_label.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=(2, 0)) # Span cols 0 & 1

        # Place Copy/Save buttons directly, anchored to the right of the third column
        self.snapshot_copy_button.grid(row=6, column=2, sticky=tk.E, padx=(0, 5), pady=(2,0))
        self.snapshot_save_button.grid(row=6, column=3, sticky=tk.W, padx=(0, 5), pady=(2,0)) # Place Save next to Copy in col 3

        # --- Row 7: Progress Bar ---
        self.snapshot_progress_bar.grid(row=7, column=0, columnspan=4, sticky=tk.EW, padx=5, pady=(1, 2)) # Span 4 columns
        self.snapshot_progress_bar.grid_remove() # Keep hidden initially

    def _layout_scaffold_widgets(self):
        """Arranges widgets in the Scaffold tab using grid."""
        frame = self.scaffold_frame
        frame.columnconfigure(0, weight=1)
        # Column 1 for the open folder button

        # Row 0: Input Buttons Frame
        self.scaffold_input_buttons_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        # Use grid for buttons inside the frame
        self.scaffold_paste_button.grid(row=0, column=0, padx=5) # Changed from pack
        self.scaffold_load_button.grid(row=0, column=1, padx=5) # Changed from pack
        self.scaffold_clear_map_button.grid(row=0, column=2, padx=15) # Changed from pack

        # Row 1: Map Input Text Area
        self.scaffold_map_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        frame.rowconfigure(1, weight=1)

        # Row 2: Configuration Frame
        self.scaffold_config_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        # Layout items within the config frame using grid (already done)
        self.scaffold_config_frame.columnconfigure(1, weight=1)
        self.scaffold_base_dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.scaffold_base_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.scaffold_clear_base_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 2))
        self.scaffold_browse_base_button.grid(row=0, column=2, sticky=tk.W, padx=(5, 15))
        self.scaffold_format_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 2))
        self.scaffold_format_combo.grid(row=0, column=4, sticky=tk.W, padx=2)

        # Row 3: Create Button
        self.scaffold_create_button.grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=5, padx=5)

        # Row 4: Status Bar (column 0) AND Open Folder Button (column 1)
        self.scaffold_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(2,0), padx=5)
        self.scaffold_open_folder_button.grid(row=4, column=1, sticky=tk.E, pady=2, padx=5)
        self.scaffold_open_folder_button.grid_remove()

        # Row 5: Progress Bar (Spanning both columns)
        self.scaffold_progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(1,2))
        self.scaffold_progress_bar.grid_remove()


    # --- Event Handlers / Commands ---

    def _handle_initial_state(self):
        """Sets up the UI based on launch context."""
        initial_status = "Ready"
        active_tab_widget = self.snapshot_frame
        target_tab_name = self.TAB_SNAPSHOT # Default

        if self.initial_mode == 'snapshot' and self.initial_path:
            active_tab_widget = self.snapshot_frame
            target_tab_name = self.TAB_SNAPSHOT
            self.snapshot_dir_var.set(str(self.initial_path))
            initial_status = f"Ready to generate map for {self.initial_path.name}"
            # Don't auto-generate immediately, let user click if needed
            # self.after(100, self._generate_snapshot)
        elif self.initial_mode == 'scaffold_from_file' and self.initial_path:
            active_tab_widget = self.scaffold_frame
            target_tab_name = self.TAB_SCAFFOLD
            if self._load_map_from_path(self.initial_path):
                 initial_status = f"Loaded map from {self.initial_path.name}"
                 self._check_scaffold_readiness()
            else:
                 initial_status = "Error loading initial map file."
        elif self.initial_mode == 'scaffold_here' and self.initial_path:
             active_tab_widget = self.scaffold_frame
             target_tab_name = self.TAB_SCAFFOLD
             self.scaffold_base_dir_var.set(str(self.initial_path))
             initial_status = f"Ready to create structure in '{self.initial_path.name}'. Paste or load map."
             self._check_scaffold_readiness()

        self.notebook.select(active_tab_widget)
        self._update_status(initial_status, tab=target_tab_name)


    def _update_status(self, message, is_error=False, is_success=False, tab=None):
        """Helper to update the status label on the specified tab with color."""
        # Determine target tab if not specified
        if tab is None:
             try:
                 current_tab_index = self.notebook.index(self.notebook.select())
                 tab = self.TAB_SNAPSHOT if current_tab_index == 0 else self.TAB_SCAFFOLD
             except tk.TclError: # Handle case where notebook might not exist yet
                  tab = self.TAB_SNAPSHOT # Default safely

        # Remove leading "Status: " if present
        if isinstance(message, str) and message.lower().startswith("status: "):
             message = message[len("Status: "):]

        status_var = self.scaffold_status_var if tab == self.TAB_SCAFFOLD else self.snapshot_status_var
        status_label = self.scaffold_status_label if tab == self.TAB_SCAFFOLD else self.snapshot_status_label

        status_var.set(f"Status: {message}")

        # Determine color
        color = "black" # Default
        try:
            style = ttk.Style()
            default_color = style.lookup('TLabel', 'foreground')
            if is_error: color = "red"
            elif is_success: color = "#008000" # Dark Green
            else: color = default_color if default_color else "black"
        except tk.TclError: # Fallback if style lookup fails
            if is_error: color = "red"
            elif is_success: color = "green"
            else: color = "black"

        # Apply color
        try:
             status_label.config(foreground=color)
             # self.update_idletasks() # Avoid frequent calls here
        except tk.TclError: pass # Ignore errors if widget destroyed


    def _check_scaffold_readiness(self):
        """Checks if map input and base directory are set, updates status if ready."""
        try:
            # Check if widgets exist before accessing them
            if not hasattr(self, 'scaffold_map_input') or \
               not hasattr(self, 'scaffold_base_dir_var') or \
               not hasattr(self, 'scaffold_status_var'):
                return

            map_ready = bool(self.scaffold_map_input.get('1.0', tk.END).strip())
            base_dir_ready = bool(self.scaffold_base_dir_var.get())
            current_status = self.scaffold_status_var.get()

            # Update only if ready and status doesn't already indicate readiness/error/processing
            if map_ready and base_dir_ready and \
               "ready to create" not in current_status.lower() and \
               "error" not in current_status.lower() and \
               "processing" not in current_status.lower() and \
               "success" not in current_status.lower():
                 self._update_status("Ready to create structure.", is_success=True, tab=self.TAB_SCAFFOLD)
        except tk.TclError:
            pass # Ignore if widgets destroyed during check


    def _browse_snapshot_dir(self):
        """Handles snapshot source directory browsing."""
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Source Directory")
        if dir_path:
            self.snapshot_dir_var.set(dir_path)
            self._update_status("Source directory selected.", tab=self.TAB_SNAPSHOT)


    def _copy_snapshot_to_clipboard(self, show_status=True):
        """Copies the snapshot map to the clipboard, respecting exclusions."""
        map_widget = self.snapshot_map_output
        original_map_text = map_widget.get('1.0', tk.END).strip()
        tag_name = self.TAG_STRIKETHROUGH

        # Get ignore patterns from the CSV field
        custom_ignores_str = self.snapshot_ignore_var.get()
        ignore_patterns_from_csv = set(p.strip() for p in custom_ignores_str.split(',') if p.strip()) if custom_ignores_str else set()

        lines_to_copy = []
        num_lines = 0
        try:
            last_line_index = map_widget.index('end-1c')
            if last_line_index:
                num_lines = int(last_line_index.split('.')[0])
                for i in range(1, num_lines + 1):
                    line_start = f"{i}.0"
                    line_text = map_widget.get(line_start, f"{i}.end")
                    if not line_text.strip(): continue

                    # Check strikethrough tag on content
                    content_start_index, _ = self._get_content_range(widget=map_widget, line_start_index=line_start, line_text=line_text)
                    is_struck_through = False
                    if content_start_index:
                        tags_on_content = map_widget.tag_names(content_start_index)
                        is_struck_through = tag_name in tags_on_content
                    if is_struck_through: continue

                    # Check against CSV ignores
                    item_name = line_text.strip().rstrip('/')
                    is_ignored_by_csv = False
                    if item_name and ignore_patterns_from_csv:
                        for pattern in ignore_patterns_from_csv:
                            if fnmatch.fnmatch(item_name, pattern) or \
                               (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(item_name, pattern.rstrip('/\\'))):
                                is_ignored_by_csv = True; break
                    if is_ignored_by_csv: continue

                    lines_to_copy.append(line_text)

        except tk.TclError as e:
             print(f"ERROR Copy: Error processing text widget content: {e}")
             messagebox.showerror("Error", f"Error preparing text for copy:\n{e}")
             if show_status: self._update_status("Error during copy preparation.", is_error=True, tab=self.TAB_SNAPSHOT)
             return False

        # Join and copy
        final_text = "\n".join(lines_to_copy)

        # Status/Clipboard Logic
        status_msg = ""
        is_error = False
        is_success = False
        copied = False
        if final_text:
            try:
                pyperclip.copy(final_text)
                original_non_blank_lines = len([line for line in original_map_text.splitlines() if line.strip()])
                if len(lines_to_copy) < original_non_blank_lines and original_map_text:
                     status_msg = "Map (with exclusions) copied."
                else: status_msg = "Map copied to clipboard."
                is_success = True; copied = True
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Could not copy to clipboard:\n{e}")
                status_msg = "Failed to copy map to clipboard."; is_error = True
        elif not original_map_text:
            if show_status: messagebox.showwarning("No Content", "Nothing to copy.")
            status_msg = "Copy failed: No map content."; is_error = True
        else:
            if show_status: messagebox.showwarning("Empty Result", "All lines were excluded, nothing copied.")
            status_msg = "Copy failed: All lines excluded."; is_error = True

        if show_status:
             self._update_status(status_msg, is_error=is_error, is_success=is_success, tab=self.TAB_SNAPSHOT)
        return copied


    def _save_snapshot_as(self):
        """Saves the currently displayed snapshot map text to a file."""
        # Saves the raw text currently in the widget, not filtered text
        map_widget = self.snapshot_map_output
        try:
            map_text_to_save = map_widget.get('1.0', tk.END) # Get full text including final newline
            # Check if content is just whitespace or error message
            if not map_text_to_save.strip() or map_text_to_save.strip().startswith("Error:"):
                 messagebox.showwarning("No Content", "Nothing valid to save.")
                 self._update_status("Save failed: No valid map content.", is_error=True, tab=self.TAB_SNAPSHOT)
                 return
        except tk.TclError:
             messagebox.showerror("Error", "Could not retrieve map text.")
             self._update_status("Save failed: Could not get map text.", is_error=True, tab=self.TAB_SNAPSHOT)
             return

        # Suggest filename based on root
        suggested_filename = "directory_map.txt"
        try:
             first_line = map_text_to_save.splitlines()[0].strip()
             root_name = first_line.rstrip('/') if first_line else ""
             if root_name:
                 safe_root_name = re.sub(r'[<>:"/\\|?*]', '_', root_name)
                 if not safe_root_name: safe_root_name = "map"
                 suggested_filename = f"{safe_root_name}_map.txt"
        except IndexError: pass

        # Ask for save path
        file_path = filedialog.asksaveasfilename(
            initialfile=suggested_filename,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Directory Map As..."
        )
        if not file_path:
            self._update_status("Save cancelled.", tab=self.TAB_SNAPSHOT)
            return

        # Write to file
        saved_filename = Path(file_path).name
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(map_text_to_save)
            self._update_status(f"Map saved to {saved_filename}", is_success=True, tab=self.TAB_SNAPSHOT)
        except Exception as e:
            messagebox.showerror("File Save Error", f"Could not save file:\n{e}")
            self._update_status(f"Failed to save map to {saved_filename}", is_error=True, tab=self.TAB_SNAPSHOT)


    def _browse_scaffold_base_dir(self):
        """Handles scaffold base directory browsing."""
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Base Directory for Scaffolding")
        if dir_path:
            self.scaffold_base_dir_var.set(dir_path)
            self._update_status(f"Base directory set to '{Path(dir_path).name}'.", is_success=True, tab=self.TAB_SCAFFOLD)
            self._check_scaffold_readiness()


    def _paste_map_input(self):
        """Pastes map text from clipboard into scaffold input."""
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                 # Clear existing tags before pasting
                 self.scaffold_map_input.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)
                 self.scaffold_map_input.delete('1.0', tk.END)
                 self.scaffold_map_input.insert('1.0', clipboard_content)
                 self._update_status("Pasted map from clipboard.", is_success=True, tab=self.TAB_SCAFFOLD)
                 self._check_scaffold_readiness()
            else:
                 self._update_status("Clipboard is empty.", tab=self.TAB_SCAFFOLD)
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not paste from clipboard:\n{e}")
            self._update_status("Failed to paste from clipboard.", is_error=True, tab=self.TAB_SCAFFOLD)


    def _load_map_from_path(self, file_path_obj):
        """Helper to load map from a Path object into scaffold input."""
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                map_content = f.read()
            # Clear existing tags before loading
            self.scaffold_map_input.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)
            self.scaffold_map_input.delete('1.0', tk.END)
            self.scaffold_map_input.insert('1.0', map_content)
            return True
        except Exception as e:
            messagebox.showerror("File Load Error", f"Could not load map file:\n{file_path_obj.name}\n\n{e}")
            return False


    def _load_map_file(self):
        """Handles loading map file into scaffold input."""
        file_path = filedialog.askopenfilename(
             filetypes=[("Text Files", "*.txt"), ("Map Files", "*.map"), ("All Files", "*.*")],
             title="Load Directory Map File"
        )
        if file_path:
             loaded_ok = self._load_map_from_path(Path(file_path))
             if loaded_ok:
                 self._update_status(f"Loaded map from {Path(file_path).name}", is_success=True, tab=self.TAB_SCAFFOLD)
                 self._check_scaffold_readiness()
             else:
                 self._update_status("Error loading map file.", is_error=True, tab=self.TAB_SCAFFOLD)


    # --- Click Handler Helper Methods ---

    def _get_line_info(self, widget, tk_index):
        """Gets line number, start/end indices, text, stripped text, and indent."""
        try:
            char_at_index = widget.get(tk_index)
            if not char_at_index or char_at_index.isspace():
                 line_start_check = widget.index(f"{tk_index} linestart")
                 line_end_check = widget.index(f"{tk_index} lineend")
                 if widget.compare(tk_index, ">=", line_end_check): return None

            line_start = widget.index(f"{tk_index} linestart")
            line_end = widget.index(f"{tk_index} lineend")
            line_num = int(line_start.split('.')[0])
            line_text = widget.get(line_start, line_end)
            stripped_text = line_text.strip()

            if not stripped_text: return None

            leading_spaces = len(line_text) - len(line_text.lstrip())
            return {
                "num": line_num, "start": line_start, "end": line_end,
                "text": line_text, "stripped": stripped_text, "indent": leading_spaces
            }
        except tk.TclError: return None

    def _get_content_range(self, widget, line_start_index, line_text=None):
        """Calculates the start/end indices of non-whitespace content."""
        try:
            if line_text is None:
                 line_text = widget.get(line_start_index, f"{line_start_index} lineend")
            stripped_text = line_text.strip()
            if not stripped_text: return None, None

            leading_spaces = len(line_text) - len(line_text.lstrip())
            content_len = len(stripped_text)
            content_start_idx = f"{line_start_index} + {leading_spaces} chars"
            content_end_idx = f"{content_start_idx} + {content_len} chars"
            return content_start_idx, content_end_idx
        except tk.TclError: return None, None

    def _toggle_tag_on_range(self, widget, tag_name, apply_action, start_idx, end_idx):
        """Applies or removes a tag on a specific text range."""
        if not start_idx or not end_idx: return
        try:
            if apply_action: widget.tag_add(tag_name, start_idx, end_idx)
            else: widget.tag_remove(tag_name, start_idx, end_idx)
        except tk.TclError as e: print(f"ERROR: Failed to toggle tag '{tag_name}' on range {start_idx}-{end_idx}: {e}")

    def _get_descendant_lines(self, widget, start_line_num, start_indent):
        """Identifies line indices for descendants based on indentation."""
        descendant_lines = []
        current_check_line_num = start_line_num + 1
        while True:
            current_check_start = f"{current_check_line_num}.0"
            if not widget.compare(current_check_start, "<", "end-1c"): break
            current_check_text = widget.get(current_check_start, f"{current_check_line_num}.end")
            stripped_check = current_check_text.strip()
            if not stripped_check: current_check_line_num += 1; continue
            current_check_indent = len(current_check_text) - len(current_check_text.lstrip())
            if current_check_indent > start_indent:
                descendant_lines.append((current_check_line_num, current_check_start))
            else: break
            current_check_line_num += 1
        return descendant_lines

    def _update_ignore_csv(self, item_name, add_action):
        """Parses, updates, and sets the snapshot ignore CSV string var. Returns True if changed."""
        if not item_name: return False
        changed = False
        current_csv_str = self.snapshot_ignore_var.get()
        ignore_set = set(p.strip() for p in current_csv_str.split(',') if p.strip()) if current_csv_str else set()
        if add_action:
            if item_name not in ignore_set: ignore_set.add(item_name); changed = True
        else:
            if item_name in ignore_set: ignore_set.remove(item_name); changed = True
        if changed:
            new_csv_str = ", ".join(sorted(list(ignore_set)))
            self.snapshot_ignore_var.set(new_csv_str)
        return changed

    def _is_directory_heuristic(self, widget, line_info):
        """Determines if a line likely represents a directory using heuristics."""
        if line_info["stripped"].endswith('/'): return True
        next_line_num = line_info["num"] + 1
        next_line_start = f"{next_line_num}.0"
        if widget.compare(next_line_start, "<", "end-1c"):
            next_line_text = widget.get(next_line_start, f"{next_line_num}.end")
            if next_line_text.strip():
                 next_indent = len(next_line_text) - len(next_line_text.lstrip())
                 if next_indent > line_info["indent"]: return True
        return False

    # --- Refactored Click Handlers ---

    def _handle_snapshot_map_click(self, event):
        """Handles clicks on the snapshot map output area using helpers."""
        widget = self.snapshot_map_output
        tag_name = self.TAG_STRIKETHROUGH

        if str(widget.cget("state")) != tk.NORMAL: return

        try:
            clicked_info = self._get_line_info(widget, f"@{event.x},{event.y}")
            if not clicked_info: return

            content_start_idx, _ = self._get_content_range(widget, clicked_info["start"], clicked_info["text"])
            if not content_start_idx: return

            initial_tags = widget.tag_names(content_start_idx)
            apply_tag_action = tag_name not in initial_tags

            lines_to_process = [(clicked_info["num"], clicked_info["start"], clicked_info["text"])]
            if self._is_directory_heuristic(widget, clicked_info):
                descendants = self._get_descendant_lines(widget, clicked_info["num"], clicked_info["indent"])
                for d_num, d_start in descendants:
                    d_text = widget.get(d_start, f"{d_num}.end")
                    lines_to_process.append((d_num, d_start, d_text))

            ignore_set_changed = False
            for line_num, line_start, line_text in lines_to_process:
                stripped_text = line_text.strip()
                item_name = stripped_text.rstrip('/')
                if not item_name: continue

                c_start, c_end = self._get_content_range(widget, line_start, line_text)
                self._toggle_tag_on_range(widget, tag_name, apply_tag_action, c_start, c_end)

                if self._update_ignore_csv(item_name, apply_tag_action):
                    ignore_set_changed = True

            if ignore_set_changed:
                status_action = "Added item(s) to" if apply_tag_action else "Removed item(s) from"
                self._update_status(f"{status_action} custom ignores.", tab=self.TAB_SNAPSHOT)

            if ignore_set_changed and self.snapshot_auto_copy_var.get():
                 self._copy_snapshot_to_clipboard(show_status=False)

        except Exception as e:
            print(f"ERROR: Unhandled exception in _handle_snapshot_map_click: {e}")
            import traceback; traceback.print_exc()


    def _handle_scaffold_map_click(self, event):
        """Handles clicks on the scaffold map input area using helpers."""
        widget = self.scaffold_map_input
        tag_name = self.TAG_STRIKETHROUGH

        if str(widget.cget("state")) != tk.NORMAL: return

        try:
            clicked_info = self._get_line_info(widget, f"@{event.x},{event.y}")
            if not clicked_info: return

            content_start_idx, _ = self._get_content_range(widget, clicked_info["start"], clicked_info["text"])
            if not content_start_idx: return

            initial_tags = widget.tag_names(content_start_idx)
            apply_tag_action = tag_name not in initial_tags

            lines_to_process = [(clicked_info["num"], clicked_info["start"], clicked_info["text"])]
            descendants = self._get_descendant_lines(widget, clicked_info["num"], clicked_info["indent"])
            for d_num, d_start in descendants:
                 d_text = widget.get(d_start, f"{d_num}.end")
                 lines_to_process.append((d_num, d_start, d_text))

            for line_num, line_start, line_text in lines_to_process:
                c_start, c_end = self._get_content_range(widget, line_start, line_text)
                self._toggle_tag_on_range(widget, tag_name, apply_tag_action, c_start, c_end)

        except Exception as e:
            print(f"ERROR: Unhandled exception in _handle_scaffold_map_click: {e}")
            import traceback; traceback.print_exc()


    # --- Threading / Queue Helpers ---

    def _start_background_task(self, target_func, args, queue_obj, button_widget,
                               progressbar_widget, status_msg, tab_name, progress_mode='indeterminate',
                               queue_check_func=None):
        """Handles common UI prep and thread starting for background tasks."""
        # 1. Prepare UI
        button_widget.config(state=tk.DISABLED)
        if progressbar_widget:
            # Use widget object directly if available
            pb_widget_obj = progressbar_widget
            if pb_widget_obj:
                pb_widget_obj['value'] = 0
                pb_widget_obj['mode'] = progress_mode
                pb_widget_obj.grid() # Show progress bar
                if progress_mode == 'indeterminate':
                    pb_widget_obj.start()
                self.update_idletasks() # Ensure UI updates before thread start
            else:
                print(f"Warning: Progress bar widget object not found for {tab_name}")
                progressbar_widget = None # Avoid errors later? Or rely on hasattr check?

        self._update_status(status_msg, tab=tab_name)

        # 2. Create and Start the thread
        # Determine which thread attribute to store based on tab
        thread_attr = "snapshot_thread" if tab_name == self.TAB_SNAPSHOT else "scaffold_thread"

        thread = threading.Thread(
            target=target_func,
            args=args + (queue_obj,), # Add queue to the arguments for the target
            daemon=True
        )
        setattr(self, thread_attr, thread) # Store thread object
        thread.start()

        # 3. Start checking the queue using the appropriate checker function
        if queue_check_func:
             self.after(100, queue_check_func)
        else:
             print(f"Warning: No queue check function provided for task on tab '{tab_name}'")
             # Reset UI if queue check won't happen
             button_widget.config(state=tk.NORMAL)
             if progressbar_widget and hasattr(self, progressbar_widget.winfo_name()):
                 progressbar_widget.stop()
                 progressbar_widget.grid_remove()

        # Return thread object (optional, maybe not needed if stored)
        # return thread


    def _finalize_task_ui(self, button_widget, progressbar_widget):
        """Resets button and progress bar state after task completion."""
        # Check if widgets still exist before configuring
        try:
            if progressbar_widget and progressbar_widget.winfo_exists():
                progressbar_widget.stop()
                progressbar_widget.grid_remove()
            if button_widget and button_widget.winfo_exists():
                button_widget.config(state=tk.NORMAL)
        except tk.TclError:
             print("Warning: Error finalizing task UI (widget might be destroyed).")


    # --- Refactored Trigger Methods ---

    def _generate_snapshot(self):
        """Handles the 'Generate / Regenerate Map' button click using thread helper."""
        source_dir = self.snapshot_dir_var.get()
        if not source_dir or not Path(source_dir).is_dir():
            messagebox.showwarning("Input Required", "Please select a valid source directory.")
            self._update_status("Snapshot failed: Invalid source directory.", is_error=True, tab=self.TAB_SNAPSHOT)
            return

        custom_ignores_str = self.snapshot_ignore_var.get()
        custom_ignores = set(p.strip() for p in custom_ignores_str.split(',') if p.strip()) if custom_ignores_str else None

        # --- Get format and emoji settings ---
        output_format = self.snapshot_format_var.get()
        show_emojis = self.snapshot_show_emojis_var.get()

        # Clear previous output immediately
        self.snapshot_map_output.config(state=tk.NORMAL)
        self.snapshot_map_output.delete('1.0', tk.END)
        self.snapshot_map_output.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)

        # Start background task
        self._start_background_task(
            target_func=self._snapshot_thread_target,
            args=(source_dir, custom_ignores, self.user_default_ignores, output_format, show_emojis),
            queue_obj=self.snapshot_queue,
            button_widget=self.snapshot_regenerate_button,
            progressbar_widget=self.snapshot_progress_bar,
            status_msg="Generating map...",
            tab_name=self.TAB_SNAPSHOT,
            progress_mode='indeterminate',
            queue_check_func=self._check_snapshot_queue
        )


    def _create_structure(self):
        """Handles the 'Create Structure' button click using thread helper."""
        map_widget = self.scaffold_map_input
        map_text = map_widget.get('1.0', tk.END).strip()
        base_dir = self.scaffold_base_dir_var.get()
        format_hint = self.scaffold_format_var.get()
        tag_name = self.TAG_STRIKETHROUGH

        # --- Input Validation ---
        if not map_text:
            messagebox.showwarning("Input Required", "Map input cannot be empty.")
            self._update_status("Scaffold failed: Map input empty.", is_error=True, tab=self.TAB_SCAFFOLD)
            return
        if not base_dir or not Path(base_dir).is_dir():
             messagebox.showwarning("Input Required", "Please select a valid base directory.")
             self._update_status("Scaffold failed: Invalid base directory.", is_error=True, tab=self.TAB_SCAFFOLD)
             return

        # --- Get Excluded Lines ---
        excluded_line_numbers = set()
        try:
            last_line_index = map_widget.index('end-1c')
            if last_line_index:
                num_lines = int(last_line_index.split('.')[0])
                for i in range(1, num_lines + 1):
                    line_start = f"{i}.0"
                    content_start_index, _ = self._get_content_range(widget=map_widget, line_start_index=line_start)
                    if content_start_index:
                        tags_on_content = map_widget.tag_names(content_start_index)
                        if tag_name in tags_on_content:
                            excluded_line_numbers.add(i)
        except tk.TclError as e:
             print(f"ERROR: Error reading tags during scaffold setup: {e}")
             messagebox.showerror("Error", f"Error processing map exclusions:\n{e}")
             self._update_status("Scaffold failed: Error processing exclusions.", is_error=True, tab=self.TAB_SCAFFOLD)
             return

        # --- Prep UI ---
        self.scaffold_open_folder_button.grid_remove()
        self.last_scaffold_path = None

        # --- Start Background Task ---
        self.scaffold_thread = self._start_background_task(
            target_func=self._scaffold_thread_target,
            args=(map_text, base_dir, format_hint, excluded_line_numbers),
            queue_obj=self.scaffold_queue,
            button_widget=self.scaffold_create_button,
            progressbar_widget=self.scaffold_progress_bar,
            status_msg="Processing...",
            tab_name=self.TAB_SCAFFOLD,
            progress_mode='determinate',
            queue_check_func=self._check_scaffold_queue
        )
        # Set initial maximum for progress bar
        try:
            # Check if progress bar exists before setting max
            if hasattr(self, 'scaffold_progress_bar') and self.scaffold_progress_bar.winfo_exists():
                 total_steps = len(map_text.splitlines()) - len(excluded_line_numbers)
                 self.scaffold_progress_bar['maximum'] = max(1, total_steps)
        except tk.TclError:
             print("Warning: Could not set progress bar maximum (widget destroyed?).")


    # --- Thread Target Functions ---
    def _snapshot_thread_target(self, source_dir, custom_ignores, user_ignores, output_format, show_emojis, q):
        """Calls the snapshot logic and puts result in queue."""
        try:
            map_result = logic.create_directory_snapshot(
                source_dir,
                custom_ignore_patterns=custom_ignores,                
                user_default_ignores=user_ignores,
                output_format=output_format,
                show_emojis=show_emojis
            )
            success = not map_result.startswith("Error:")
            q.put({'type': self.QUEUE_MSG_RESULT, 'success': success, 'map_text': map_result})
        except Exception as e:
             q.put({'type': self.QUEUE_MSG_RESULT, 'success': False, 'map_text': f"Error in thread: {e}"})
             print(f"--- Error in Snapshot Thread: {e} ---")
             # import traceback; traceback.print_exc() # Keep commented unless debugging

    def _scaffold_thread_target(self, map_text, base_dir, format_hint, excluded_lines, q):
        """Calls the backend logic and puts result/progress/root_name in queue."""
        created_root_name = None # Initialize
        try:
            # Capture all three return values from the logic function
            msg, success, created_root_name = logic.create_structure_from_map(
                 map_text, base_dir, format_hint,
                 excluded_lines=excluded_lines, queue=q
            )
            # Include created_root_name in the result message dictionary
            q.put({'type': self.QUEUE_MSG_RESULT, 'success': success, 'message': msg, 'root_name': created_root_name})
        except Exception as e:
            # Ensure root_name is None on exception
            q.put({'type': self.QUEUE_MSG_RESULT, 'success': False, 'message': f"Error in thread: {e}", 'root_name': None})
            print(f"--- Error in Scaffold Thread: {e} ---")
            import traceback # Keep traceback for thread errors
            traceback.print_exc()

    # --- Queue Checking Functions ---

    def _check_snapshot_queue(self):
        """Checks queue for messages from snapshot thread and updates UI."""
        try:
            while True: # Process all messages
                msg = self.snapshot_queue.get_nowait()
                msg_type = msg.get('type')

                if msg_type == self.QUEUE_MSG_RESULT:
                    success = msg['success']
                    map_text_result = msg['map_text']

                    # Update text area first
                    try: # Protect against widget destruction
                         if self.snapshot_map_output.winfo_exists():
                              self.snapshot_map_output.config(state=tk.NORMAL)
                              self.snapshot_map_output.delete('1.0', tk.END)
                              self.snapshot_map_output.insert('1.0', map_text_result)
                              self.snapshot_map_output.tag_remove(self.TAG_STRIKETHROUGH, '1.0', tk.END)
                    except tk.TclError: pass

                    # Update status & handle auto-copy
                    status_msg = "Map generated." if success else map_text_result
                    if success:
                        if self.snapshot_auto_copy_var.get():
                            copied_ok = self._copy_snapshot_to_clipboard(show_status=False)
                            status_msg = "Map generated and copied." if copied_ok else "Map generated (auto-copy failed)."
                    self._update_status(status_msg, is_error=not success, is_success=success, tab=self.TAB_SNAPSHOT)

                    # Finalize UI
                    self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar)
                    return # Stop checking

        except queue.Empty:
            # Check if thread object exists and is alive
            thread_obj = getattr(self, 'snapshot_thread', None)
            if thread_obj and thread_obj.is_alive():
                self.after(100, self._check_snapshot_queue)
            else: # Thread finished unexpectedly or doesn't exist
                # print("Warning: Snapshot thread finished but queue check found no result or thread missing.")
                self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar)

        except Exception as e:
            print(f"ERROR: Exception in _check_snapshot_queue: {e}")
            import traceback; traceback.print_exc()
            self._finalize_task_ui(self.snapshot_regenerate_button, self.snapshot_progress_bar)
            self._update_status(f"UI Error during snapshot processing: {e}", is_error=True, tab=self.TAB_SNAPSHOT)


# === Place inside DirSnapApp class in DirSnap/app.py ===

    def _check_scaffold_queue(self):
        """Checks queue for messages from scaffold thread and updates UI."""
        try:
            while True: # Process all available messages in the queue
                msg = self.scaffold_queue.get_nowait()
                msg_type = msg.get('type')

                if msg_type == self.QUEUE_MSG_PROGRESS:
                    # --- Handle Progress ---
                    current = msg.get('current', 0)
                    total = msg.get('total', 1) # Default total to 1 to avoid division by zero if needed
                    # Update progress bar safely
                    try:
                         pb = self.scaffold_progress_bar
                         if pb and pb.winfo_exists():
                              # Ensure total is at least 1 for maximum
                              pb_max = max(1, total)
                              if pb['maximum'] != pb_max: pb['maximum'] = pb_max
                              # Ensure mode is determinate if we have progress values
                              if pb['mode'] != 'determinate':
                                  pb.stop(); pb['mode'] = 'determinate'
                              pb['value'] = current
                    except (tk.TclError, AttributeError) as e:
                         print(f"Warning: Error updating progress bar: {e}")
                    # --- End Handle Progress ---

                elif msg_type == self.QUEUE_MSG_RESULT:
                    success = msg.get('success', False)
                    message = msg.get('message', 'Unknown result')
                    created_root_name = msg.get('root_name') # Get the potentially None root name

                    # Update status first
                    self._update_status(message, is_error=not success, is_success=success, tab=self.TAB_SCAFFOLD)
                    # Finalize common UI elements (button, progress bar)
                    self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)

                    # Handle specific success action: Show button if successful and we got a name
                    if success and created_root_name:
                        self._show_open_folder_button(created_root_name) # Pass the actual name

                    # Once result is processed, stop checking the queue for this task run
                    return

        except queue.Empty:
            # Queue is empty, check if the thread is still running
            thread_obj = getattr(self, 'scaffold_thread', None)
            if thread_obj and thread_obj.is_alive():
                # Reschedule queue check
                self.after(100, self._check_scaffold_queue)
            else:
                # Thread finished, but no result message found? Finalize UI just in case.
                # print("Warning: Scaffold thread finished but queue check found no result or thread missing.") # Optional debug
                self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)

        except Exception as e:
            # Catch any other unexpected errors during queue processing
            print(f"ERROR: Exception in _check_scaffold_queue: {e}")
            import traceback
            traceback.print_exc()
            self._finalize_task_ui(self.scaffold_create_button, self.scaffold_progress_bar)
            self._update_status(f"UI Error during scaffold processing: {e}", is_error=True, tab=self.TAB_SCAFFOLD)

# === Place inside DirSnapApp class in DirSnap/app.py ===

    def _show_open_folder_button(self, created_root_name):
         """
         Shows the 'Open Output Folder' button if the specified path exists.
         Uses the actual created root name passed from the backend logic.
         """
         try:
              base_dir = self.scaffold_base_dir_var.get()
              # Check if we received necessary info
              if not base_dir or not created_root_name:
                  print("Warning: Cannot show open folder button - missing base dir or created root name.")
                  self.last_scaffold_path = None # Ensure path is None
                  # Make sure button is hidden if it was previously visible
                  if hasattr(self, 'scaffold_open_folder_button') and self.scaffold_open_folder_button.winfo_exists():
                      self.scaffold_open_folder_button.grid_remove()
                  return

              # Construct the full path using the provided (already sanitized) root name
              full_path = Path(base_dir) / created_root_name
              if full_path.is_dir():
                  # Path exists, store it and show the button
                  self.last_scaffold_path = full_path
                  if hasattr(self, 'scaffold_open_folder_button') and self.scaffold_open_folder_button.winfo_exists():
                       self.scaffold_open_folder_button.grid() # Use grid to show it
              else:
                   # Path doesn't exist - this indicates an internal issue if success was reported
                   print(f"Internal Warning: Scaffold reported success, but final path check failed for: {full_path}")
                   self._update_status(f"Structure created (Warning: Output path check failed!)", is_success=True, tab=self.TAB_SCAFFOLD)
                   self.last_scaffold_path = None # Ensure path is None
                   # Make sure button is hidden
                   if hasattr(self, 'scaffold_open_folder_button') and self.scaffold_open_folder_button.winfo_exists():
                       self.scaffold_open_folder_button.grid_remove()

         except tk.TclError:
              # Handle cases where the widget might have been destroyed
              print("Info: TclError likely means scaffold tab widget destroyed during _show_open_folder_button.")
              self.last_scaffold_path = None
              pass
         except Exception as e:
              print(f"Warning: Error checking/showing open folder button: {e}")
              self._update_status(f"Structure created (Info: Could not enable 'Open Folder' button)", is_success=True, tab=self.TAB_SCAFFOLD)
              self.last_scaffold_path = None # Ensure path is None on error
              # Make sure button is hidden
              if hasattr(self, 'scaffold_open_folder_button') and self.scaffold_open_folder_button.winfo_exists():
                  self.scaffold_open_folder_button.grid_remove()

    def _open_last_scaffold_folder(self):
        """Opens the last successfully created scaffold output folder."""
        if not self.last_scaffold_path:
            self._update_status("No scaffold output folder recorded.", is_error=True, tab=self.TAB_SCAFFOLD)
            return

        path_to_open = Path(self.last_scaffold_path)
        if not path_to_open.is_dir():
             self._update_status(f"Output folder not found: {self.last_scaffold_path}", is_error=True, tab=self.TAB_SCAFFOLD)
             return

        path_str = str(path_to_open)
        try:
            print(f"Info: Attempting to open folder: {path_str}")
            if sys.platform == "win32":
                os.startfile(path_str)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', path_str], check=True)
            else: # Linux and other POSIX variants
                subprocess.run(['xdg-open', path_str], check=True)
            self._update_status(f"Opened folder: {path_to_open.name}", is_success=True, tab=self.TAB_SCAFFOLD)

        except FileNotFoundError:
             err_msg = f"Cmd not found for platform {sys.platform}."
             messagebox.showerror("Error opening folder", err_msg)
             self._update_status("Error opening folder: command not found.", is_error=True, tab=self.TAB_SCAFFOLD)
        except subprocess.CalledProcessError as e:
              err_msg = f"System command failed: {e}"
              messagebox.showerror("Error opening folder", err_msg)
              self._update_status(f"Error opening folder: {e}", is_error=True, tab=self.TAB_SCAFFOLD)
        except Exception as e:
            err_msg = f"Could not open folder '{path_to_open.name}':\n{e}"
            messagebox.showerror("Error opening folder", err_msg)
            self._update_status(f"Error opening folder: {e}", is_error=True, tab=self.TAB_SCAFFOLD)

# filename: dirsnap/app.py
    # ... (other methods) ...

    # --- Help Menu Methods ---

    def _show_about(self):
        """Displays the About dialog."""
        messagebox.showinfo(
            "About DirSnap",
            f"Directory Mapper & Scaffolder\n\n"
            f"Version: {APP_VERSION}\n\n"
            "A utility to create directory maps and scaffold structures from them.\n\n"
            "Asa V. Schaeffer & Gemini Advanced 2.5 Pro (experimental)",
            parent=self
        )

    def _view_readme(self):
        """Attempts to open the README.md file."""
        try:
            # Assume README.md is in the parent directory of the script's location
            # This might need adjustment depending on packaging/installation structure
            script_dir = Path(__file__).parent
            readme_path = script_dir.parent / "README.md" # Go up one level from dirsnap/

            if not readme_path.is_file():
                 # Try finding it in the current working directory as a fallback
                 readme_path_cwd = Path.cwd() / "README.md"
                 if readme_path_cwd.is_file():
                     readme_path = readme_path_cwd
                 else:
                     messagebox.showwarning("README Not Found",
                                           f"Could not find README.md at expected locations:\n"
                                           f"- {readme_path}\n"
                                           f"- {readme_path_cwd}",
                                           parent=self)
                     return

            # Open the file using platform-specific methods (similar to _open_config_file)
            path_str = str(readme_path.resolve())
            print(f"Info: Attempting to open README file: {path_str}")
            if sys.platform == "win32":
                os.startfile(path_str)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', path_str], check=True)
            else: # Linux and other POSIX variants
                subprocess.run(['xdg-open', path_str], check=True)

        except FileNotFoundError:
             err_msg = f"Could not find the command (e.g., 'open' or 'xdg-open') needed to open the file on this system ({sys.platform})."
             messagebox.showerror("Error Opening File", err_msg, parent=self)
        except subprocess.CalledProcessError as e:
              err_msg = f"The command to open the file failed:\n{e}"
              messagebox.showerror("Error Opening File", err_msg, parent=self)
        except Exception as e:
            err_msg = f"An unexpected error occurred while trying to open the README file:\n{e}"
            messagebox.showerror("Error Opening File", err_msg, parent=self)

    # ... (Rest of the class) ...


# --- Main execution block for testing the UI directly ---
if __name__ == '__main__':
    print("Running app.py directly for UI testing...")
    # Example: Test snapshot mode by default
    # app = DirSnapApp()

    # Example: Test scaffold_here mode
    test_scaffold_path = str(Path('./_ui_test_scaffold_here').resolve())
    Path(test_scaffold_path).mkdir(exist_ok=True) # Ensure dir exists
    print(f"Testing 'scaffold_here' mode with path: {test_scaffold_path}")
    app = DirSnapApp(initial_path=test_scaffold_path, initial_mode='scaffold_here')

    app.mainloop()

    # Clean up test dir
    try:
        if Path(test_scaffold_path).exists():
            shutil.rmtree(test_scaffold_path)
            print(f"Cleaned up test dir: {test_scaffold_path}")
    except Exception as e:
        print(f"Could not clean up test dir: {e}")

