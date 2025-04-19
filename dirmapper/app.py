# dirmapper/app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkFont # Import font submodule
import pyperclip # Dependency: pip install pyperclip
from pathlib import Path
import sys
import os
import subprocess
import fnmatch
import shutil
import re
import threading
import queue

# Use relative import to access logic.py within the same package
try:
    from . import logic
except ImportError:
    # Fallback for running app.py directly for testing UI (not recommended for final)
    print("Warning: Running app.py directly. Attempting to import logic module from current directory.")
    import logic

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

# --- DirMapperApp Class ---
class DirMapperApp(tk.Tk):
    def __init__(self, initial_path=None, initial_mode='snapshot'):
        super().__init__()

        self.scaffold_queue = queue.Queue()
        self.snapshot_queue = queue.Queue()

        self.initial_path = Path(initial_path) if initial_path else None
        self.initial_mode = initial_mode

        self.title("Directory Mapper & Scaffolder")
        self.minsize(550, 450)

        # --- Configure Custom TTK Style for Clear Button ---
        style = ttk.Style(self)
        try:
            # Attempt to get Entry background color for seamless look
            entry_bg = style.lookup('TEntry', 'fieldbackground')
            # Use a slightly dimmer foreground for the 'x'
            text_color = style.lookup('TLabel', 'foreground') # Get default text color
            # You might need to experiment with system color names like 'SystemButtonFace', 'SystemWindow' as fallbacks
            default_font = tkFont.nametofont("TkDefaultFont")
            print(f"Debug: Found default font: {default_font.actual()}")
            
        except tk.TclError:
            print("Warning: Could not look up theme colors, using fallback.")
            entry_bg = 'SystemWindow' # Common fallback background
            text_color = 'black'      # Default text color

        # Modify style configuration in __init__ in dirmapper/app.py

        # Define the custom style - Add borderwidth and relief
        style.configure('ClearButton.TButton',
                        foreground='grey',
                        borderwidth=0,      # <<<--- ADD THIS
                        relief='flat',      # <<<--- ADD THIS
                        padding=0           # Keep padding minimal? Or maybe small like 1? Test 0.
                        # NO background or focuscolor set yet
                       )

        # Optional: Map hover/active states (only change foreground)
        style.map('ClearButton.TButton',
                  foreground=[('active', text_color), ('pressed', text_color)]
                  # Still no background map
                  )
        # --- End Style Configuration ---

        # --- Main UI Structure ---
        self.notebook = ttk.Notebook(self)
        self.snapshot_frame = ttk.Frame(self.notebook, padding="10")
        self.scaffold_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.snapshot_frame, text='Snapshot (Dir -> Map)')
        self.notebook.add(self.scaffold_frame, text='Scaffold (Map -> Dir)')
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # --- Populate Tabs ---
        self._create_snapshot_widgets()
        self._layout_snapshot_widgets()
        self._create_scaffold_widgets()
        self._layout_scaffold_widgets()

        self.after(50, self._handle_initial_state)

    # --- Widget Creation Methods ---

    def _create_snapshot_widgets(self):
        """Creates widgets for the Snapshot tab."""
        # Labels
        self.snapshot_dir_label = ttk.Label(self.snapshot_frame, text="Source Directory:")
        self.snapshot_ignore_label = ttk.Label(self.snapshot_frame, text="Custom Ignores (comma-sep):")
        # Default Ignores Label
        common_defaults = sorted(list(logic.DEFAULT_IGNORE_PATTERNS))[:4]
        default_ignores_text = f"Ignoring defaults like: {', '.join(common_defaults)}, ..."
        self.snapshot_default_ignores_label = ttk.Label(self.snapshot_frame, text=default_ignores_text, foreground="grey")
        Tooltip(self.snapshot_default_ignores_label, "Also ignoring:\n" + "\n".join(sorted(list(logic.DEFAULT_IGNORE_PATTERNS)))) # Tooltip for full list

        # Entries & Buttons
        self.snapshot_dir_var = tk.StringVar()
        self.snapshot_dir_entry = ttk.Entry(self.snapshot_frame, textvariable=self.snapshot_dir_var, width=50)
        self.snapshot_browse_button = ttk.Button(self.snapshot_frame, text="Browse...", command=self._browse_snapshot_dir)
        self.snapshot_clear_dir_button = ttk.Button(self.snapshot_frame, text="X", width=2, command=lambda: self.snapshot_dir_var.set(''), style='ClearButton.TButton')

        self.snapshot_ignore_var = tk.StringVar()
        self.snapshot_ignore_entry = ttk.Entry(self.snapshot_frame, textvariable=self.snapshot_ignore_var, width=50)
        self.snapshot_clear_ignore_button = ttk.Button(self.snapshot_frame, text="X", width=2, command=lambda: self.snapshot_ignore_var.set(''), style='ClearButton.TButton')

        self.snapshot_regenerate_button = ttk.Button(self.snapshot_frame, text="Generate / Regenerate Map", command=self._generate_snapshot)

        # Checkbox
        self.snapshot_auto_copy_var = tk.BooleanVar(value=False)
        self.snapshot_auto_copy_check = ttk.Checkbutton(self.snapshot_frame, text="Auto-copy on generation", variable=self.snapshot_auto_copy_var)

        # Output Area
        self.snapshot_map_output = scrolledtext.ScrolledText(self.snapshot_frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED)
        self.snapshot_map_output.tag_configure("strikethrough", overstrike=True, foreground="grey50") # Configure the tag
        self.snapshot_map_output.bind("<Button-1>", self._handle_snapshot_map_click) # Bind left-click

        # Action Buttons
        self.snapshot_copy_button = ttk.Button(self.snapshot_frame, text="Copy to Clipboard", command=self._copy_snapshot_to_clipboard)
        self.snapshot_save_button = ttk.Button(self.snapshot_frame, text="Save Map As...", command=self._save_snapshot_as)

        # Snapshot Status
        self.snapshot_status_var = tk.StringVar(value="Status: Ready")
        self.snapshot_status_label = ttk.Label(self.snapshot_frame, textvariable=self.snapshot_status_var, anchor=tk.W)

        # Snapshot Progress Bar
        self.snapshot_progress_bar = ttk.Progressbar(
            self.snapshot_frame,
            orient=tk.HORIZONTAL,
            length=100,
            mode='indeterminate' # Indeterminate for snapshot initially
        )

        # --- Add Tooltips ---
        Tooltip(self.snapshot_browse_button, "Select the root directory to generate a map for.")
        Tooltip(self.snapshot_ignore_entry, "Enter comma-separated names/patterns to ignore (e.g., .git, *.log, temp/)")
        Tooltip(self.snapshot_regenerate_button, "Generate/Refresh the directory map based on current settings.")
        Tooltip(self.snapshot_auto_copy_check, "If checked, automatically copy the map to clipboard upon generation.")
        Tooltip(self.snapshot_copy_button, "Copy the generated map text to the clipboard.")
        Tooltip(self.snapshot_save_button, "Save the generated map text to a file.")
        Tooltip(self.snapshot_clear_dir_button, "Clear directory path")
        Tooltip(self.snapshot_clear_ignore_button, "Clear custom ignores")
        Tooltip(self.snapshot_map_output, "Click on a line to toggle exclusion from copy.")

    def _create_scaffold_widgets(self):
        """Creates widgets for the Scaffold tab."""
        # Input Area & Buttons
        self.scaffold_input_buttons_frame = ttk.Frame(self.scaffold_frame)
        self.scaffold_paste_button = ttk.Button(self.scaffold_input_buttons_frame, text="Paste Map", command=self._paste_map_input)
        self.scaffold_load_button = ttk.Button(self.scaffold_input_buttons_frame, text="Load Map...", command=self._load_map_file)
        self.scaffold_clear_map_button = ttk.Button(self.scaffold_input_buttons_frame, text="Clear Map", command=lambda: self.scaffold_map_input.delete('1.0', tk.END))
        self.scaffold_map_input = scrolledtext.ScrolledText(self.scaffold_frame, wrap=tk.WORD, height=15, width=60)

        self.scaffold_map_input.tag_configure("strikethrough", overstrike=True, foreground="grey50")
        self.scaffold_map_input.bind("<Button-1>", self._handle_scaffold_map_click)

        # Config Row Frame
        self.scaffold_config_frame = ttk.Frame(self.scaffold_frame)
        self.scaffold_base_dir_label = ttk.Label(self.scaffold_config_frame, text="Base Directory:")
        self.scaffold_base_dir_var = tk.StringVar()
        self.scaffold_base_dir_entry = ttk.Entry(self.scaffold_config_frame, textvariable=self.scaffold_base_dir_var, width=40)
        self.scaffold_browse_base_button = ttk.Button(self.scaffold_config_frame, text="Browse...", command=self._browse_scaffold_base_dir)
        self.scaffold_clear_base_dir_button = ttk.Button(self.scaffold_config_frame, text="X", width=2, command=lambda: self.scaffold_base_dir_var.set(''), style='ClearButton.TButton')

        self.scaffold_format_label = ttk.Label(self.scaffold_config_frame, text="Input Format:")
        self.scaffold_format_var = tk.StringVar(value="Auto-Detect")
        self.scaffold_format_combo = ttk.Combobox(
            self.scaffold_config_frame, textvariable=self.scaffold_format_var,
            values=["Auto-Detect", "Spaces (2)", "Spaces (4)", "Tabs", "Tree", "Generic"], # Updated list
            state='readonly'
        )

        # Action Button
        self.scaffold_create_button = ttk.Button(self.scaffold_frame, text="Create Structure", command=self._create_structure)

        # Status Bar
        self.scaffold_status_var = tk.StringVar(value="Status: Ready")
        self.scaffold_status_label = ttk.Label(self.scaffold_frame, textvariable=self.scaffold_status_var, anchor=tk.W)

        # --- Open Folder Button ---
        self.scaffold_open_folder_button = ttk.Button(
            self.scaffold_frame,
            text="Open Output Folder",
            command=self._open_last_scaffold_folder
            # state=tk.DISABLED # Start disabled, will be hidden by layout initially
        )
        self.last_scaffold_path = None # Variable to store the path

        # --- SCAFFOLD PROGRESS BAR ---
        if not hasattr(self, 'scaffold_progress_bar'):
            self.scaffold_progress_bar = ttk.Progressbar(
                self.scaffold_frame,
                orient=tk.HORIZONTAL,
                length=100,
                mode='determinate'
            )

        # --- Add Tooltips ---
        Tooltip(self.scaffold_paste_button, "Paste map text from clipboard into the input area.")
        Tooltip(self.scaffold_load_button, "Load map text from a file into the input area.")
        Tooltip(self.scaffold_clear_map_button, "Clear the map input area.")
        Tooltip(self.scaffold_map_input, "Enter or paste your directory map here.\nClick lines to toggle exclusion from creation.")
        Tooltip(self.scaffold_browse_base_button, "Select the existing parent directory where the new structure will be created.")
        Tooltip(self.scaffold_clear_base_dir_button, "Clear base directory path")
        Tooltip(self.scaffold_format_combo, "Select the expected format of the input map (Auto-Detect recommended).")
        Tooltip(self.scaffold_create_button, "Create the directory structure defined in the map input within the selected base directory.")
        Tooltip(self.scaffold_open_folder_button, "Open the folder created by the last successful scaffold operation.")

    # --- Layout Methods  ---

    def _layout_snapshot_widgets(self):
        """Arranges widgets in the Snapshot tab using grid (Ultra Simple - No Sub-frames)."""
        self.snapshot_frame.columnconfigure(1, weight=1)

        # Row 0: Source Directory
        self.snapshot_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=3)
        self.snapshot_clear_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 2)) # Place in same cell
        self.snapshot_browse_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)

        # Row 1: Custom Ignores Entry
        self.snapshot_ignore_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_ignore_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=3)
        self.snapshot_clear_ignore_button.grid(row=1, column=1, sticky=tk.E, padx=(0, 2)) # Place in same cell
        # Column 2 is free in this row

        # Row 2: Default Ignores Info Label
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5))

        # Row 3: Controls (Generate Button, Checkbox)
        self.snapshot_regenerate_button.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.snapshot_auto_copy_check.grid(row=3, column=1, sticky=tk.W, padx=15, pady=5)

        # Row 4: Action Buttons (Copy, Save)
        self.snapshot_copy_button.grid(row=4, column=1, sticky=tk.E, padx=5, pady=5)
        self.snapshot_save_button.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        # Row 5: Output Text Area
        self.snapshot_map_output.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.snapshot_frame.rowconfigure(5, weight=1)

        # Row 6: Status Bar
        self.snapshot_status_label.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(2,0), padx=5)

        # Row 7: Progress Bar
        self.snapshot_progress_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(1,2))
        self.snapshot_progress_bar.grid_remove() # Hide initially

    def _layout_scaffold_widgets(self):
        """Arranges widgets in the Scaffold tab using grid."""
        # Configure column 0 to expand, pushing column 1 (where button is) to the right
        self.scaffold_frame.columnconfigure(0, weight=1)
        # No weight needed for column 1 - it just holds the button

        # Row 0: Input Buttons (remains the same)
        self.scaffold_input_buttons_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2) # Span both columns
        self.scaffold_paste_button.grid(row=0, column=0, padx=5)
        self.scaffold_load_button.grid(row=0, column=1, padx=5)
        self.scaffold_clear_map_button.grid(row=0, column=2, padx=15)

        # Row 1: Map Input Text Area (remains the same)
        self.scaffold_map_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5) # Span both columns
        self.scaffold_frame.rowconfigure(1, weight=1) # Allow text area to expand vertically

        # Row 2: Configuration Frame (remains the same)
        self.scaffold_config_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5) # Span both columns
        # ... (widgets inside config frame need appropriate col spanning if not already done) ...
        # Make sure config frame's internal layout works within the spanned cell
        self.scaffold_config_frame.columnconfigure(1, weight=1) # Let Base Dir Entry expand within frame
        self.scaffold_base_dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.scaffold_base_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.scaffold_clear_base_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 2))
        self.scaffold_browse_base_button.grid(row=0, column=2, sticky=tk.W, padx=(5, 15))
        self.scaffold_format_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 2))
        self.scaffold_format_combo.grid(row=0, column=4, sticky=tk.W, padx=2)


        # Row 3: Create Button (remains the same)
        self.scaffold_create_button.grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=5, padx=5) # Span both columns

        # --- ADJUSTED LAYOUT for Status/Button (Row 4) and Progress (Row 5) ---
        # Row 4: Status Bar (column 0) AND Open Folder Button (column 1)
        self.scaffold_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(2,0), padx=5) # Status label in expanding column 0
        self.scaffold_open_folder_button.grid(row=4, column=1, sticky=tk.E, pady=2, padx=5) # Button in fixed-size column 1 on the right
        self.scaffold_open_folder_button.grid_remove() # Keep hidden initially

        # Row 5: Progress Bar (Spanning both columns) - Initially hidden
        self.scaffold_progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(1,2)) # Progress bar below, spanning width
        if hasattr(self, 'scaffold_progress_bar'): # Check if exists before removing
            self.scaffold_progress_bar.grid_remove() # Hide initially

    # --- Event Handlers / Commands ---

    def _handle_initial_state(self):
        """Sets up the UI based on launch context."""
        initial_status = "Ready"
        active_tab_widget = self.snapshot_frame

        if self.initial_mode == 'snapshot' and self.initial_path:
            active_tab_widget = self.snapshot_frame
            self.snapshot_dir_var.set(str(self.initial_path))
            initial_status = f"Ready to generate map for {self.initial_path.name}"
            self.after(100, self._generate_snapshot)
        elif self.initial_mode == 'scaffold_from_file' and self.initial_path:
            active_tab_widget = self.scaffold_frame
            if self._load_map_from_path(self.initial_path):
                 initial_status = f"Loaded map from {self.initial_path.name}"
                 self._check_scaffold_readiness() # Check if ready after load
            else:
                 initial_status = "Error loading initial map file."
                 # Error message shown by _load_map_from_path helper
        elif self.initial_mode == 'scaffold_here' and self.initial_path:
             active_tab_widget = self.scaffold_frame
             self.scaffold_base_dir_var.set(str(self.initial_path))
             initial_status = f"Ready to create structure in '{self.initial_path.name}'. Paste or load map."
             self._check_scaffold_readiness() # Check if ready (map might be empty)

        self.notebook.select(active_tab_widget)
        target_tab_name = 'snapshot' if active_tab_widget == self.snapshot_frame else 'scaffold'
        self._update_status(initial_status, tab=target_tab_name)


    def _update_status(self, message, is_error=False, is_success=False, tab='scaffold'):
        """Helper to update the status label on the specified tab with color."""
        if isinstance(message, str) and message.lower().startswith("status: "):
             message = message[len("Status: "):]

        status_var = self.scaffold_status_var if tab == 'scaffold' else self.snapshot_status_var
        status_label = self.scaffold_status_label if tab == 'scaffold' else self.snapshot_status_label

        status_var.set(f"Status: {message}")

        color = "black"
        try:
            style = ttk.Style()
            default_color = style.lookup('TLabel', 'foreground')
            if is_error: color = "red"
            elif is_success: color = "#008000" # Dark Green
            else: color = default_color if default_color else "black"
        except tk.TclError:
            if is_error: color = "red"
            elif is_success: color = "green" # Fallback brighter green
            else: color = "black"

        try:
             status_label.config(foreground=color)
             self.update_idletasks()
        except tk.TclError: pass


    def _check_scaffold_readiness(self):
        """Checks if map input and base directory are set, updates status if ready."""
        map_ready = bool(self.scaffold_map_input.get('1.0', tk.END).strip())
        base_dir_ready = bool(self.scaffold_base_dir_var.get())
        current_status = self.scaffold_status_var.get()

        if map_ready and base_dir_ready and "ready to create" not in current_status.lower() and "error" not in current_status.lower():
            self._update_status("Ready to create structure.", is_success=True, tab='scaffold')


    def _browse_snapshot_dir(self):
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Source Directory")
        if dir_path:
            self.snapshot_dir_var.set(dir_path)
            self._update_status("Source directory selected.", tab='snapshot')

    def _generate_snapshot(self):
        """Handles the 'Generate / Regenerate Map' button click.
        Starts snapshot generation in a thread and manages indeterminate progress bar.
        """
        # 1. Get Inputs & Validate (as before)
        source_dir = self.snapshot_dir_var.get()
        if not source_dir or not Path(source_dir).is_dir():
            messagebox.showwarning("Input Required", "Please select a valid source directory.")
            self._update_status("Snapshot failed: Invalid source directory.", is_error=True, tab='snapshot')
            return

        custom_ignores_str = self.snapshot_ignore_var.get()
        custom_ignores = set(p.strip() for p in custom_ignores_str.split(',') if p.strip()) if custom_ignores_str else None

        # --- Start Threading Logic ---
        # 2. Prepare UI for processing
        self.snapshot_regenerate_button.config(state=tk.DISABLED) # Disable button
        self.snapshot_map_output.config(state=tk.NORMAL) # Ensure output is usable
        self.snapshot_map_output.delete('1.0', tk.END) # Clear previous output
        self.snapshot_progress_bar['mode'] = 'indeterminate'
        self.snapshot_progress_bar.grid() # Show progress bar
        self.snapshot_progress_bar.start() # Start indeterminate animation
        self.update_idletasks() # Ensure UI updates
        self._update_status("Generating map...", tab='snapshot')

        # 3. Create and Start the thread
        print("DEBUG: Creating and starting snapshot thread...") # Debug print
        self.snapshot_thread = threading.Thread(
            target=self._snapshot_thread_target,
            args=(source_dir, custom_ignores, self.snapshot_queue),
            daemon=True
        )
        self.snapshot_thread.start()
        # 4. Start checking the queue
        print("DEBUG: Starting snapshot queue check loop.") # Debug print
        self.after(100, self._check_snapshot_queue) # Check queue every 100ms

    def _snapshot_thread_target(self, source_dir, custom_ignores, q):
        """Calls the snapshot logic and puts result in queue."""
        try:
            # --- IMPORTANT ---
            # We need to modify logic.create_directory_snapshot later
            # to ACCEPT the queue, although it won't use it for progress updates.
            # It's good practice to pass it if the pattern requires it,
            # or we modify the pattern. Let's assume we modify logic.py later.
            map_result = logic.create_directory_snapshot(
                 source_dir,
                 custom_ignore_patterns=custom_ignores
                 # queue=q # Pass queue eventually if needed by pattern/future features
            )
            # Determine success based on result string
            success = not map_result.startswith("Error:")
            q.put({'type': 'result', 'success': success, 'map_text': map_result})

        except Exception as e:
             q.put({'type': 'result', 'success': False, 'map_text': f"Error in thread: {e}"})
             import traceback
             traceback.print_exc()

    def _check_snapshot_queue(self):
        """Checks queue for messages from snapshot thread and updates UI."""
        try:
            while True: # Process all messages currently in queue
                msg = self.snapshot_queue.get_nowait()

                if msg['type'] == 'result':
                    # --- Handle final result ---
                    success = msg['success']
                    map_text_result = msg['map_text']

                    # Stop and hide progress bar
                    self.snapshot_progress_bar.stop()
                    self.snapshot_progress_bar.grid_remove()

                    # Update text area (ensure state is normal first)
                    self.snapshot_map_output.config(state=tk.NORMAL)
                    self.snapshot_map_output.delete('1.0', tk.END) # Clear again just in case
                    self.snapshot_map_output.insert('1.0', map_text_result)
                    # We leave it NORMAL for the click interaction now
                    # self.snapshot_map_output.config(state=tk.DISABLED) # Disable after insert

                    # Update status bar
                    status_msg = "Map generated." if success else map_text_result
                    copied_ok_auto = False
                    if success:
                        # Handle auto-copy if enabled
                        if self.snapshot_auto_copy_var.get():
                            copied_ok_auto = self._copy_snapshot_to_clipboard(show_status=False) # Copy silently
                            status_msg = "Map generated and copied." if copied_ok_auto else "Map generated (auto-copy failed)."
                    self._update_status(status_msg, is_error=not success, is_success=success, tab='snapshot')

                    # Re-enable button
                    self.snapshot_regenerate_button.config(state=tk.NORMAL)
                    return # Stop checking queue

        except queue.Empty:
            # Queue is empty, check again later if thread is still alive
            if self.snapshot_thread.is_alive():
                self.after(100, self._check_snapshot_queue)
            else:
                # Thread finished unexpectedly
                self.snapshot_progress_bar.stop()
                self.snapshot_progress_bar.grid_remove()
                self.snapshot_regenerate_button.config(state=tk.NORMAL)
                # Maybe update status?
                # self._update_status("Snapshot generation finished unexpectedly.", is_error=True, tab='snapshot')

        except Exception as e:
            # Handle unexpected errors in the queue checking logic itself
            print(f"ERROR: Exception in _check_snapshot_queue: {e}")
            import traceback
            traceback.print_exc()
            self.snapshot_progress_bar.stop()
            self.snapshot_progress_bar.grid_remove()
            self.snapshot_regenerate_button.config(state=tk.NORMAL)
            self._update_status(f"UI Error during snapshot processing: {e}", is_error=True, tab='snapshot')

    def _copy_snapshot_to_clipboard(self, show_status=True):
        """Copies the snapshot map to the clipboard, excluding lines that are
        either struck-through OR match a pattern in the custom ignore field.
        """
        map_widget = self.snapshot_map_output
        original_map_text = map_widget.get('1.0', tk.END).strip()

        # 1. Get ignore patterns from the CSV field
        custom_ignores_str = self.snapshot_ignore_var.get()
        # Ensure patterns are stripped and non-empty
        ignore_patterns_from_csv = set(p.strip() for p in custom_ignores_str.split(',') if p.strip()) if custom_ignores_str else set()

        lines_to_copy = []
        try:
            # Determine the last line number
            last_line_index = map_widget.index('end-1c') # Index of last char
            if not last_line_index: # Handle empty widget case
                 num_lines = 0
            else:
                 num_lines = int(last_line_index.split('.')[0])

            for i in range(1, num_lines + 1):
                line_start = f"{i}.0"
                line_end = f"{i}.end"
                line_text = map_widget.get(line_start, line_end)

                # Skip blank lines in output
                if not line_text.strip():
                    continue

                # 2. Check for strikethrough tag
                tags_on_line = map_widget.tag_names(line_start)
                is_struck_through = "strikethrough" in tags_on_line
                # print(f"DEBUG Copy: Line {i}, Struck: {is_struck_through}, Text: '{line_text}'") # Optional debug

                if is_struck_through:
                    continue # Skip struck-through lines

                # 3. If not struck through, check against CSV ignores
                #    Extract item name (simple version: strip whitespace and trailing slash)
                #    This needs to be consistent with how names are added from clicks
                item_name = line_text.strip().rstrip('/')
                # Optional: Strip common list prefixes if they might appear (unlikely here)
                # item_name = logic.PREFIX_STRIP_RE_GENERIC.sub("", item_name).strip()

                is_ignored_by_csv = False
                if item_name and ignore_patterns_from_csv: # Only check if we have a name and patterns
                    for pattern in ignore_patterns_from_csv:
                        # Use fnmatch for pattern matching (e.g., *.log) and handle dirs
                        if fnmatch.fnmatch(item_name, pattern) or \
                           (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(item_name, pattern.rstrip('/\\'))):
                            is_ignored_by_csv = True
                            # print(f"DEBUG Copy: Line {i} item '{item_name}' matched CSV pattern '{pattern}'") # Optional debug
                            break

                if is_ignored_by_csv:
                    continue # Skip lines matching CSV ignores

                # 4. If not struck through AND not ignored by CSV, add it
                lines_to_copy.append(line_text)

        except tk.TclError as e:
             print(f"ERROR Copy: Error processing text widget content: {e}")
             messagebox.showerror("Error", f"Error preparing text for copy:\n{e}")
             if show_status: self._update_status("Error during copy preparation.", is_error=True, tab='snapshot')
             return False # Indicate copy failed

        # 5. Join and copy
        final_text = "\n".join(lines_to_copy)

        # --- Status/Clipboard Logic ---
        status_msg = ""
        is_error = False
        is_success = False
        copied = False

        if final_text:
            try:
                pyperclip.copy(final_text)
                # Be more specific about success
                if len(lines_to_copy) < num_lines and original_map_text:
                     status_msg = "Map (with exclusions) copied to clipboard."
                else: # Copied everything or map was empty
                     status_msg = "Map copied to clipboard."
                is_success = True
                copied = True
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Could not copy to clipboard:\n{e}")
                status_msg = "Failed to copy map to clipboard."
                is_error = True
        elif not original_map_text: # Check if original map was empty
            if show_status: messagebox.showwarning("No Content", "Nothing to copy.")
            status_msg = "Copy failed: No map content."
            is_error = True # Treat as non-success
        else: # Original map had content, but all lines were excluded
            if show_status: messagebox.showwarning("Empty Result", "All lines were excluded, nothing copied.")
            status_msg = "Copy failed: All lines excluded."
            is_error = True # Treat as non-success

        if show_status:
             self._update_status(status_msg, is_error=is_error, is_success=is_success, tab='snapshot')
        return copied # Return True if copy succeeded, False otherwise
    
    def _handle_snapshot_map_click(self, event):
        """Handles clicks on the snapshot map output area.
        Toggles strikethrough tag ON TEXT ONLY for the clicked item and its
        descendants (if it's a directory). Updates ignore CSV list,
        and optionally auto-copies.
        """
        widget = self.snapshot_map_output
        tag_name = "strikethrough"

        if str(widget.cget("state")) != tk.NORMAL:
             return

        try:
            clicked_index_str = widget.index(f"@{event.x},{event.y}")
            # Ensure click wasn't on empty space after last line
            if not widget.get(clicked_index_str, f"{clicked_index_str} +1c").strip():
                 return

            clicked_line_start = widget.index(f"{clicked_index_str} linestart")
            clicked_line_end = widget.index(f"{clicked_index_str} lineend")
            clicked_line_num = int(clicked_line_start.split('.')[0])
            clicked_line_text = widget.get(clicked_line_start, clicked_line_end)

            # Ignore clicks on completely blank lines
            if not clicked_line_text.strip():
                return

            # --- Calculate initial line info ---
            clicked_stripped_text = clicked_line_text.strip()
            clicked_leading_spaces = len(clicked_line_text) - len(clicked_line_text.lstrip())
            clicked_content_start_index = f"{clicked_line_start} + {clicked_leading_spaces} chars"

            # --- Determine if Directory (Heuristic) ---
            is_likely_directory = False
            if clicked_stripped_text.endswith('/'):
                is_likely_directory = True
            else:
                next_line_num = clicked_line_num + 1
                next_line_start = f"{next_line_num}.0"
                if widget.compare(next_line_start, "<", "end-1c"):
                    next_line_text = widget.get(next_line_start, f"{next_line_num}.end")
                    # Check if next line is not blank before calculating indent
                    if next_line_text.strip():
                         next_indent = len(next_line_text) - len(next_line_text.lstrip())
                         if next_indent > clicked_leading_spaces:
                             is_likely_directory = True

            # --- Determine Action based on initial click ---
            initial_tags = widget.tag_names(clicked_content_start_index)
            was_initially_struck_through = tag_name in initial_tags
            apply_tag_action = not was_initially_struck_through # If it wasn't struck, action is to apply tag

            # --- Identify all lines to process (clicked + children if directory) ---
            lines_to_process_indices = [(clicked_line_num, clicked_line_start)] # List of (line_num, line_start_index)
            if is_likely_directory:
                # Start checking from the line AFTER the clicked one
                current_check_line_num = clicked_line_num + 1
                while True:
                    current_check_start = f"{current_check_line_num}.0"
                    # Stop if we've gone past the end of the text widget
                    if not widget.compare(current_check_start, "<", "end-1c"):
                        break

                    current_check_text = widget.get(current_check_start, f"{current_check_line_num}.end")
                    # Skip blank lines when checking hierarchy
                    if not current_check_text.strip():
                        current_check_line_num += 1
                        continue

                    current_check_indent = len(current_check_text) - len(current_check_text.lstrip())

                    if current_check_indent > clicked_leading_spaces:
                        # It's a child/descendant, add to list
                        lines_to_process_indices.append((current_check_line_num, current_check_start))
                    else:
                        # Indentation is same or less, stop searching down this branch
                        break
                    current_check_line_num += 1

            # --- Process all identified lines ---
            ignore_set_changed = False
            # Get current CSV ignores ONCE before the loop
            current_csv_str = self.snapshot_ignore_var.get()
            ignore_set = set(p.strip() for p in current_csv_str.split(',') if p.strip()) if current_csv_str else set()

            for line_num, line_start_index in lines_to_process_indices:
                line_end_index = f"{line_num}.end"
                line_text_loop = widget.get(line_start_index, line_end_index)
                stripped_text_loop = line_text_loop.strip()
                item_name = stripped_text_loop.rstrip('/')

                # Calculate content range for this specific line
                leading_spaces_loop = len(line_text_loop) - len(line_text_loop.lstrip())
                content_len_loop = len(stripped_text_loop)
                content_start_idx_loop = f"{line_start_index} + {leading_spaces_loop} chars"
                content_end_idx_loop = f"{content_start_idx_loop} + {content_len_loop} chars"

                # Apply or remove tag
                if apply_tag_action:
                    widget.tag_add(tag_name, content_start_idx_loop, content_end_idx_loop)
                    if item_name and item_name not in ignore_set:
                        ignore_set.add(item_name)
                        ignore_set_changed = True
                else:
                    widget.tag_remove(tag_name, content_start_idx_loop, content_end_idx_loop)
                    if item_name and item_name in ignore_set:
                        ignore_set.remove(item_name)
                        ignore_set_changed = True

            # --- Update CSV and Status Bar (only if changes were made) ---
            status_action = ""
            if ignore_set_changed:
                new_csv_str = ", ".join(sorted(list(ignore_set)))
                self.snapshot_ignore_var.set(new_csv_str)
                # Determine overall action for status message
                if apply_tag_action:
                     status_action = "Added item(s) to"
                else:
                     status_action = "Removed item(s) from"
                self._update_status(f"{status_action} custom ignores.", tab='snapshot')

            # --- Auto-Copy Check ---
            # Trigger if the ignore set was changed by the click action
            if ignore_set_changed and self.snapshot_auto_copy_var.get():
                 # print("DEBUG: Auto-copy triggered by click.")
                 self._copy_snapshot_to_clipboard(show_status=False)
                 # self._update_status(f"{status_action} ignores. Auto-copied.", tab='snapshot') # Optional combined status

        except tk.TclError as e:
            print(f"DEBUG: Error handling click: {e}")
            pass
        # Optional: return "break"

    def _save_snapshot_as(self):
        map_text = self.snapshot_map_output.get('1.0', tk.END).strip()
        if not map_text or map_text.startswith("Error:"):
            messagebox.showwarning("No Content", "Nothing to save.")
            self._update_status("Save failed: No map content.", is_error=True, tab='snapshot')
            return

        suggested_filename = "directory_map.txt"
        try:
            first_line = map_text.splitlines()[0].strip()
            root_name = first_line.rstrip('/') if first_line else ""
            if root_name:
                safe_root_name = re.sub(r'[<>:"/\\|?*]', '_', root_name) # Sanitize for filename
                if not safe_root_name: safe_root_name = "map"
                suggested_filename = f"{safe_root_name}_map.txt"
        except IndexError: pass

        file_path = filedialog.asksaveasfilename(
            initialfile=suggested_filename,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Directory Map As..."
        )
        if file_path:
            saved_filename = Path(file_path).name
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(map_text)
                self._update_status(f"Map saved to {saved_filename}", is_success=True, tab='snapshot')
            except Exception as e:
                messagebox.showerror("File Save Error", f"Could not save file:\n{e}")
                self._update_status(f"Failed to save map to {saved_filename}", is_error=True, tab='snapshot')
        else:
            self._update_status("Save cancelled.", tab='snapshot')


    def _browse_scaffold_base_dir(self):
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Base Directory for Scaffolding")
        if dir_path:
            self.scaffold_base_dir_var.set(dir_path)
            self._update_status(f"Base directory set to '{Path(dir_path).name}'.", is_success=True, tab='scaffold')
            self._check_scaffold_readiness()


    def _paste_map_input(self):
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.scaffold_map_input.config(state=tk.NORMAL)
                self.scaffold_map_input.delete('1.0', tk.END)
                self.scaffold_map_input.insert('1.0', clipboard_content)
                self._update_status("Pasted map from clipboard.", is_success=True, tab='scaffold')
                self._check_scaffold_readiness()
            else:
                self._update_status("Clipboard is empty.", tab='scaffold')
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not paste from clipboard:\n{e}")
            self._update_status("Failed to paste from clipboard.", is_error=True, tab='scaffold')


    def _load_map_from_path(self, file_path_obj):
        """Helper to load map from a Path object."""
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                map_content = f.read()
            self.scaffold_map_input.config(state=tk.NORMAL)
            self.scaffold_map_input.delete('1.0', tk.END)
            self.scaffold_map_input.insert('1.0', map_content)
            return True
        except Exception as e:
            messagebox.showerror("File Load Error", f"Could not load map file:\n{file_path_obj.name}\n\n{e}")
            return False


    def _load_map_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("Map Files", "*.map"), ("All Files", "*.*")],
            title="Load Directory Map File"
        )
        if file_path:
            loaded_ok = self._load_map_from_path(Path(file_path))
            if loaded_ok:
                self._update_status(f"Loaded map from {Path(file_path).name}", is_success=True, tab='scaffold')
                self._check_scaffold_readiness()
            else:
                self._update_status("Error loading map file.", is_error=True, tab='scaffold')

    def _handle_scaffold_map_click(self, event):
        """Handles clicks on the scaffold map input area.
        Toggles strikethrough tag ON TEXT ONLY for the clicked item and its
        descendants (based on indentation).
        """
        widget = self.scaffold_map_input
        tag_name = "strikethrough"

        if str(widget.cget("state")) != tk.NORMAL:
             return

        try:
            clicked_index_str = widget.index(f"@{event.x},{event.y}")
            # Ensure click wasn't on empty space after last line
            if not widget.get(clicked_index_str, f"{clicked_index_str} +1c").strip():
                 return

            clicked_line_start = widget.index(f"{clicked_index_str} linestart")
            # clicked_line_end = widget.index(f"{clicked_index_str} lineend") # Not needed immediately
            clicked_line_num = int(clicked_line_start.split('.')[0])
            clicked_line_text = widget.get(clicked_line_start, f"{clicked_line_start} lineend") # Get full line text

            # Ignore clicks on completely blank lines
            if not clicked_line_text.strip():
                return

            # --- Calculate initial line info ---
            clicked_stripped_text = clicked_line_text.strip()
            clicked_leading_spaces = len(clicked_line_text) - len(clicked_line_text.lstrip())
            # Calculate start index of actual content for checking tags
            content_start_index_clicked = f"{clicked_line_start} + {clicked_leading_spaces} chars"

            # --- Determine Action based on initial click ---
            initial_tags = widget.tag_names(content_start_index_clicked)
            was_initially_struck_through = tag_name in initial_tags
            apply_tag_action = not was_initially_struck_through # If it wasn't struck, action is to apply tag

            # --- Identify all lines to process (clicked + children) ---
            # We need indentation to determine hierarchy
            lines_to_process_indices = [(clicked_line_num, clicked_line_start)] # List of (line_num, line_start_index)

            # Check subsequent lines for children only if the clicked line could be a parent
            # (No need to look for children if clicking the last line, for example)
            current_check_line_num = clicked_line_num + 1
            while True:
                current_check_start = f"{current_check_line_num}.0"
                # Stop if we've gone past the end of the text widget
                if not widget.compare(current_check_start, "<", "end-1c"):
                    break

                current_check_text = widget.get(current_check_start, f"{current_check_line_num}.end")
                # Skip blank lines when checking hierarchy
                if not current_check_text.strip():
                    current_check_line_num += 1
                    continue

                current_check_indent = len(current_check_text) - len(current_check_text.lstrip())

                if current_check_indent > clicked_leading_spaces:
                    # It's a child/descendant, add to list
                    lines_to_process_indices.append((current_check_line_num, current_check_start))
                else:
                    # Indentation is same or less, stop searching down this branch
                    break
                current_check_line_num += 1

            # --- Process all identified lines (Apply/Remove Tags Visually) ---
            for line_num, line_start_index in lines_to_process_indices:
                line_end_index = f"{line_num}.end"
                line_text_loop = widget.get(line_start_index, line_end_index)
                stripped_text_loop = line_text_loop.strip()

                # Calculate content range for this specific line
                leading_spaces_loop = len(line_text_loop) - len(line_text_loop.lstrip())
                # Avoid tagging if line is actually blank after stripping potential prefixes later
                if not stripped_text_loop:
                    continue
                content_len_loop = len(stripped_text_loop)
                content_start_idx_loop = f"{line_start_index} + {leading_spaces_loop} chars"
                content_end_idx_loop = f"{content_start_idx_loop} + {content_len_loop} chars"

                # Apply or remove tag
                if apply_tag_action:
                    widget.tag_add(tag_name, content_start_idx_loop, content_end_idx_loop)
                else:
                    widget.tag_remove(tag_name, content_start_idx_loop, content_end_idx_loop)

        except tk.TclError as e:
            print(f"DEBUG: Error handling scaffold click: {e}")
            pass

    def _create_structure(self):
        """Handles the 'Create Structure' button click.
        Starts the structure creation in a separate thread and manages progress bar.
        """
        # 1. Get Inputs & Validate (as before)
        map_widget = self.scaffold_map_input
        map_text = map_widget.get('1.0', tk.END).strip()
        base_dir = self.scaffold_base_dir_var.get()
        format_hint = self.scaffold_format_var.get()
        tag_name = "strikethrough"

        if not map_text:
            messagebox.showwarning("Input Required", "Map input cannot be empty.")
            self._update_status("Scaffold failed: Map input empty.", is_error=True, tab='scaffold')
            return
        if not base_dir or not Path(base_dir).is_dir():
             messagebox.showwarning("Input Required", "Please select a valid base directory.")
             self._update_status("Scaffold failed: Invalid base directory.", is_error=True, tab='scaffold')
             return

        # --- Get Excluded Lines (as before) ---
        excluded_line_numbers = set()
        try:
            # ... (logic to populate excluded_line_numbers based on tags - same as before) ...
            last_line_index = map_widget.index('end-1c')
            if last_line_index:
                num_lines = int(last_line_index.split('.')[0])
                for i in range(1, num_lines + 1):
                    line_start = f"{i}.0"
                    line_text = map_widget.get(line_start, f"{i}.end")
                    stripped_text = line_text.strip()
                    if not stripped_text: continue
                    leading_spaces = len(line_text) - len(line_text.lstrip())
                    content_start_index = f"{line_start} + {leading_spaces} chars"
                    tags_on_content = map_widget.tag_names(content_start_index)
                    if tag_name in tags_on_content:
                        excluded_line_numbers.add(i)
        except tk.TclError as e:
             # ... (error handling for tag reading - as before) ...
             return
        # -------------------------------------
        # --- Start Threading Logic ---
        # 2. Prepare UI for processing
        self.scaffold_create_button.config(state=tk.DISABLED) # Disable button
        self.scaffold_open_folder_button.grid_remove() # Ensure open button is hidden
        self.last_scaffold_path = None # Reset last path
        self.scaffold_progress_bar['value'] = 0 # Reset progress bar
        self.scaffold_progress_bar['mode'] = 'determinate' # Assuming determinate for scaffold
        # Calculate total steps (approximate: number of lines to potentially process)
        # A more accurate count will come from logic.py later
        total_steps = len(map_text.splitlines()) # Initial estimate
        if total_steps > 0 :
             self.scaffold_progress_bar['maximum'] = total_steps
        self.scaffold_progress_bar.grid() # Show progress bar
        self.update_idletasks() # <<<--- THIS LINE ---<<<
        self._update_status("Processing...", tab='scaffold')

        # 3. Create and Start the thread
        self.scaffold_thread = threading.Thread(
            target=self._scaffold_thread_target,
            args=(map_text, base_dir, format_hint, excluded_line_numbers, self.scaffold_queue),
            daemon=True # Allows app to exit even if thread is running (optional)
        )
        self.scaffold_thread.start()
        # 4. Start checking the queue
        self.after(100, self._check_scaffold_queue) # Check queue every 100ms

# In dirmapper/app.py -> DirMapperApp class

    def _scaffold_thread_target(self, map_text, base_dir, format_hint, excluded_lines, q): # 'q' is the queue object
        """Calls the backend logic and puts result/progress in queue."""
        try:
            # --- Ensure queue is passed here ---
            msg, success = logic.create_structure_from_map(
                 map_text,
                 base_dir,
                 format_hint,
                 excluded_lines=excluded_lines,
                 queue=q # <<<--- MAKE SURE THIS ARGUMENT IS PRESENT AND UNCOMMENTED
            )
            # Add a slight delay before putting the final result,
            # ensuring any final progress messages get processed first by the UI loop (optional)

            q.put({'type': 'result', 'success': success, 'message': msg})

        except Exception as e:
             q.put({'type': 'result', 'success': False, 'message': f"Error in thread: {e}"})
             import traceback
             print("--- Error in Scaffold Thread ---")
             traceback.print_exc()
             print("------------------------------")




    def _check_scaffold_queue(self):
        """Checks queue for messages from scaffold thread and updates UI."""
        try:
            while True: # Process all messages currently in queue
                msg = self.scaffold_queue.get_nowait()
                if msg['type'] == 'progress':
                    # --- Handle progress updates (when logic.py sends them) ---
                    current = msg.get('current', 0)
                    total = msg.get('total', self.scaffold_progress_bar['maximum'])
                    if total > 0:
                         self.scaffold_progress_bar['maximum'] = total
                         self.scaffold_progress_bar['value'] = current
                         # Optional: Update status text too
                         # percentage = int((current / total) * 100)
                         # self._update_status(f"Processing... {percentage}%", tab='scaffold')
                    else: # If total is 0, maybe switch to indeterminate?
                         self.scaffold_progress_bar['mode'] = 'indeterminate'
                         self.scaffold_progress_bar.start()

                elif msg['type'] == 'result':
                    
                    # --- Handle final result ---
                    success = msg['success']
                    message = msg['message']

                    self._update_status(message, is_error=not success, is_success=success, tab='scaffold')
                    self.scaffold_progress_bar.stop() # Stop animation if indeterminate
                    self.scaffold_progress_bar.grid_remove() # Hide progress bar
                    self.scaffold_create_button.config(state=tk.NORMAL) # Re-enable button



                    # Process success state (show open button, etc.) - same logic as before
                    if success:
                        try:
                            # Get original map text again if needed, or pass base_dir/root_name from thread
                            map_text = self.scaffold_map_input.get('1.0', tk.END).strip() # Get fresh copy
                            base_dir = self.scaffold_base_dir_var.get()
                            created_root_name = map_text.splitlines()[0].strip().rstrip('/')
                            safe_root_name = re.sub(r'[<>:"/\\|?*]', '_', created_root_name)
                            if not safe_root_name: safe_root_name = "_sanitized_empty_name_"

                            if created_root_name:
                                full_path = Path(base_dir) / safe_root_name
                                if full_path.is_dir():
                                    self.last_scaffold_path = full_path
                                    self.scaffold_open_folder_button.grid() # Show button
                                else: # Should not happen if success is True, but safety check
                                     print(f"Warning: Scaffold thread reported success, but path not found: {full_path}")
                                     self._update_status(f"{message} (Warning: Output path check failed!)", is_success=True, tab='scaffold') # Still show success
                            # else case for not finding root name... (as before)

                        except Exception as e:
                             # Handle error determining success path (as before)
                             print(f"Warning: Error processing success state in queue check: {e}")
                             self._update_status(f"{message} (Info: Could not enable 'Open Folder' button)", is_success=True, tab='scaffold')
                             self.last_scaffold_path = None

                    return # Stop checking queue once result is processed

        except queue.Empty:
            # Queue is empty, check again later if thread is still alive
            if self.scaffold_thread.is_alive():
                self.after(100, self._check_scaffold_queue)
            else:
                # Thread finished unexpectedly without putting result?
                print("Warning: Scaffold thread finished but queue check found no result.")
                self.scaffold_progress_bar.stop()
                self.scaffold_progress_bar.grid_remove()
                self.scaffold_create_button.config(state=tk.NORMAL)
                # Optionally update status to indicate potential issue
                # self._update_status("Processing finished unexpectedly.", is_error=True, tab='scaffold')

        except Exception as e:
            # Handle unexpected errors in the queue checking logic itself
            print(f"ERROR: Exception in _check_scaffold_queue: {e}")
            import traceback
            traceback.print_exc()
            self.scaffold_progress_bar.stop()
            self.scaffold_progress_bar.grid_remove()
            self.scaffold_create_button.config(state=tk.NORMAL)
            self._update_status(f"UI Error during processing: {e}", is_error=True, tab='scaffold')

    def _open_last_scaffold_folder(self):
        """Opens the last successfully created scaffold output folder."""
        if not self.last_scaffold_path:
            self._update_status("No scaffold output folder recorded.", is_error=True, tab='scaffold')
            return

        path_to_open = Path(self.last_scaffold_path) # Ensure it's a Path object
        if not path_to_open.is_dir():
            # Maybe the base dir was stored if root couldn't be determined? Check that.
            if self.last_scaffold_path.is_dir():
                path_to_open = self.last_scaffold_path # Open base dir instead
            else:
                self._update_status(f"Output folder not found: {self.last_scaffold_path}", is_error=True, tab='scaffold')
                return

        path_str = str(path_to_open)
        try:
            print(f"Info: Attempting to open folder: {path_str}") # Use Info level
            if sys.platform == "win32":
                os.startfile(path_str)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', path_str], check=True)
            else: # Linux and other POSIX variants
                subprocess.run(['xdg-open', path_str], check=True)
            # Update status only on successful command execution (or assumed success for startfile)
            self._update_status(f"Opened folder: {path_to_open.name}", is_success=True, tab='scaffold')

        except FileNotFoundError:
            err_msg = f"Could not find command ('open' or 'xdg-open') to open folder for platform {sys.platform}."
            messagebox.showerror("Error", err_msg)
            self._update_status("Error opening folder: command not found.", is_error=True, tab='scaffold')
        except subprocess.CalledProcessError as e:
            err_msg = f"System command failed to open folder:\n{e}"
            messagebox.showerror("Error", err_msg)
            self._update_status(f"Error opening folder: {e}", is_error=True, tab='scaffold')
        except Exception as e:
            err_msg = f"Could not open folder '{path_to_open.name}':\n{e}"
            messagebox.showerror("Error", err_msg)
            self._update_status(f"Error opening folder: {e}", is_error=True, tab='scaffold')


# --- Main execution block for testing the UI directly ---
if __name__ == '__main__':
    print("Running app.py directly for UI testing...")
    # Example: Test snapshot mode by default
    # app = DirMapperApp()

    # Example: Test scaffold_here mode
    test_scaffold_path = str(Path('./_ui_test_scaffold_here').resolve())
    Path(test_scaffold_path).mkdir(exist_ok=True) # Ensure dir exists
    print(f"Testing 'scaffold_here' mode with path: {test_scaffold_path}")
    app = DirMapperApp(initial_path=test_scaffold_path, initial_mode='scaffold_here')

    app.mainloop()

    # Clean up test dir
    try:
        if Path(test_scaffold_path).exists():
            shutil.rmtree(test_scaffold_path)
            print(f"Cleaned up test dir: {test_scaffold_path}")
    except Exception as e:
        print(f"Could not clean up test dir: {e}")
