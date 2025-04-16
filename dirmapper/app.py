# dirmapper/app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkFont # Import the font submodule with an alias
import pyperclip # Dependency: pip install pyperclip
from pathlib import Path
import sys
import os # Needed for os.startfile (optional feature)
import subprocess

# Use relative import to access logic.py within the same package
try:
    from . import logic
except ImportError:
    # Fallback for running app.py directly for testing UI (not recommended for final)
    import logic

# Add this class definition near the top of dirmapper/app.py

class Tooltip:
    """
    Creates a tooltip (pop-up) window for a Tkinter widget.
    """
    def __init__(self, widget, text, delay=500, wraplength=180):
        self.widget = widget
        self.text = text
        self.delay = delay  # milliseconds to delay showing the tooltip
        self.wraplength = wraplength # pixels before wrapping text
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip) # Hide on click too
        self.tip_window = None
        self.id = None

    def schedule_tooltip(self, event=None):
        """Schedules the tooltip to appear after a delay."""
        self.hide_tooltip() # Hide any existing tooltip immediately
        # Schedule show_tooltip() to run after self.delay milliseconds
        self.id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self, event=None):
        """Displays the tooltip window."""
        # Get widget position relative to screen
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert") # Get coordinates of the widget
        # Calculate position below the widget
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        # Creates a Toplevel window (a pop-up)
        self.tip_window = tk.Toplevel(self.widget)
        # Removes window decorations (title bar, etc.)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}") # Position near widget

        label = tk.Label(self.tip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1, # Light yellow background
                         wraplength=self.wraplength, padx=4, pady=2)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        """Hides the tooltip window."""
        # Cancel the scheduled appearance (if it hasn't appeared yet)
        scheduled_id = self.id
        self.id = None
        if scheduled_id:
            self.widget.after_cancel(scheduled_id)

        # Destroy the tooltip window if it exists
        tip = self.tip_window
        self.tip_window = None
        if tip:
            tip.destroy()

class DirMapperApp(tk.Tk):
    def __init__(self, initial_path=None, initial_mode='snapshot'):
        super().__init__()

        self.initial_path = Path(initial_path) if initial_path else None
        self.initial_mode = initial_mode

        self.title("Directory Mapper & Scaffolder")
        # Set minimum size
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

        # --- Main UI Structure ---
        self.notebook = ttk.Notebook(self)

        # --- Create Frames for Tabs ---
        self.snapshot_frame = ttk.Frame(self.notebook, padding="10")
        self.scaffold_frame = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.snapshot_frame, text='Snapshot (Dir -> Map)')
        self.notebook.add(self.scaffold_frame, text='Scaffold (Map -> Dir)')

        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # --- Populate Tabs ---
        self._create_snapshot_widgets()
        self._layout_snapshot_widgets() # Use grid layout within the frame

        self._create_scaffold_widgets()
        self._layout_scaffold_widgets() # Use grid layout within the frame

        # --- Handle Initial State ---
        # Use 'after' to ensure the main window is drawn before processing initial state
        self.after(50, self._handle_initial_state)

    # --- Widget Creation Methods ---

    def _create_snapshot_widgets(self):
        """Creates widgets for the Snapshot tab."""
        # Labels
        self.snapshot_dir_label = ttk.Label(self.snapshot_frame, text="Source Directory:")
        self.snapshot_ignore_label = ttk.Label(self.snapshot_frame, text="Custom Ignores (comma-sep):")
        # (Future: Output Format Label)

        # Entries & Buttons
        self.snapshot_dir_var = tk.StringVar()
        self.snapshot_dir_entry = ttk.Entry(self.snapshot_frame, textvariable=self.snapshot_dir_var, width=50)
        self.snapshot_browse_button = ttk.Button(self.snapshot_frame, text="Browse...", command=self._browse_snapshot_dir)
        self.snapshot_clear_dir_button = ttk.Button(
            self.snapshot_frame, text="x", width=2, # Use multiplication sign ×
            command=lambda: self.snapshot_dir_var.set(''),
            style='ClearButton.TButton' # Apply the custom style
        )
        

        self.snapshot_ignore_var = tk.StringVar()
        self.snapshot_ignore_entry = ttk.Entry(self.snapshot_frame, textvariable=self.snapshot_ignore_var, width=50)
        self.snapshot_clear_ignore_button = ttk.Button(
            self.snapshot_frame, text="x", width=2,
            command=lambda: self.snapshot_ignore_var.set(''),
            style='ClearButton.TButton' # Apply the custom style
        )
        

        # Label to show default ignores
        # Create the string for the label text - show common examples
        # Get first few defaults, sort them for consistency
        common_defaults = sorted(list(logic.DEFAULT_IGNORE_PATTERNS))[:4] # Show first 4 alphabetically
        default_ignores_text = f"Ignoring defaults like: {', '.join(common_defaults)}, ..."
        self.snapshot_default_ignores_label = ttk.Label(
            self.snapshot_frame,
            text=default_ignores_text,
            foreground="grey" # Use a standard grey color
            # For theme-aware color, would need ttk.Style lookup later:
            # style = ttk.Style()
            # disabled_color = style.lookup('TLabel', 'foreground', ('disabled',)) # Example
            # foreground=disabled_color
        )
        

        self.snapshot_regenerate_button = ttk.Button(self.snapshot_frame, text="Generate / Regenerate Map", command=self._generate_snapshot)

        # Checkbox
        self.snapshot_auto_copy_var = tk.BooleanVar(value=False) # Default OFF
        self.snapshot_auto_copy_check = ttk.Checkbutton(self.snapshot_frame, text="Auto-copy on generation", variable=self.snapshot_auto_copy_var)

        # Output Area
        self.snapshot_map_output = scrolledtext.ScrolledText(self.snapshot_frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED) # Read-only

        # Action Buttons
        self.snapshot_copy_button = ttk.Button(self.snapshot_frame, text="Copy to Clipboard", command=self._copy_snapshot_to_clipboard)
        self.snapshot_save_button = ttk.Button(self.snapshot_frame, text="Save Map As...", command=self._save_snapshot_as)

        Tooltip(self.snapshot_browse_button, "Select the root directory to generate a map for.")
        Tooltip(self.snapshot_clear_dir_button, "Clear directory path")
        Tooltip(self.snapshot_ignore_entry, "Enter comma-separated names/patterns to ignore (e.g., .git, *.log, temp/)")
        Tooltip(self.snapshot_clear_ignore_button, "Clear custom ignores")
        Tooltip(self.snapshot_regenerate_button, "Generate/Refresh the directory map based on current settings.")
        Tooltip(self.snapshot_auto_copy_check, "If checked, automatically copy the map to clipboard upon generation.")
        Tooltip(self.snapshot_copy_button, "Copy the generated map text to the clipboard.")
        Tooltip(self.snapshot_save_button, "Save the generated map text to a file.")


        # Snapshot Status Bar
        self.snapshot_status_var = tk.StringVar(value="Status: Ready")
        self.snapshot_status_label = ttk.Label(self.snapshot_frame, textvariable=self.snapshot_status_var, anchor=tk.W)

    def _create_scaffold_widgets(self):
        """Creates widgets for the Scaffold tab."""
        # Input Area & Buttons
        self.scaffold_input_buttons_frame = ttk.Frame(self.scaffold_frame)
        self.scaffold_paste_button = ttk.Button(self.scaffold_input_buttons_frame, text="Paste Map", command=self._paste_map_input)
        self.scaffold_load_button = ttk.Button(self.scaffold_input_buttons_frame, text="Load Map...", command=self._load_map_file)
        self.scaffold_map_input = scrolledtext.ScrolledText(self.scaffold_frame, wrap=tk.WORD, height=15, width=60)
        self.scaffold_clear_map_button = ttk.Button(self.scaffold_input_buttons_frame, text="Clear Map", command=lambda: self.scaffold_map_input.delete('1.0', tk.END))

        # --- Tooltips for Input Buttons ---
        Tooltip(self.scaffold_paste_button, "Paste map text from clipboard into the input area.")
        Tooltip(self.scaffold_load_button, "Load map text from a file into the input area.")

        # Config Row Frame (to group base dir and format selector)
        self.scaffold_config_frame = ttk.Frame(self.scaffold_frame)
        # Widgets inside config frame
        self.scaffold_base_dir_label = ttk.Label(self.scaffold_config_frame, text="Base Directory:")
        self.scaffold_base_dir_var = tk.StringVar()
        self.scaffold_base_dir_entry = ttk.Entry(self.scaffold_config_frame, textvariable=self.scaffold_base_dir_var, width=40)
        self.scaffold_browse_base_button = ttk.Button(self.scaffold_config_frame, text="Browse...", command=self._browse_scaffold_base_dir)
        self.scaffold_clear_base_dir_button = ttk.Button(
            self.scaffold_config_frame, text="x", width=2,
            command=lambda: self.scaffold_base_dir_var.set(''),
            style='ClearButton.TButton' # Apply the custom style
        )
        

        self.scaffold_format_label = ttk.Label(self.scaffold_config_frame, text="Input Format:")
        self.scaffold_format_var = tk.StringVar(value="Auto-Detect") # Default for future use
        self.scaffold_format_combo = ttk.Combobox(
            self.scaffold_config_frame,
            textvariable=self.scaffold_format_var,
            values=["MVP Format", "Auto-Detect", "Spaces (2)", "Spaces (4)", "Tabs", "Tree"], # Only MVP works now
            state='readonly' # Prevent typing custom values
        )
        # Set MVP format as default selected for now
        self.scaffold_format_var.set("MVP Format")

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

         # --- Add Tooltips for Config/Action ---
        Tooltip(self.scaffold_browse_base_button, "Select the existing parent directory where the new structure will be created.")
        Tooltip(self.scaffold_clear_base_dir_button, "Clear base directory path")
        Tooltip(self.scaffold_format_combo, "Select the expected format of the input map (Auto-Detect recommended).")
        Tooltip(self.scaffold_create_button, "Create the directory structure defined in the map input within the selected base directory.")
        Tooltip(self.scaffold_open_folder_button, "Open the folder created by the last successful scaffold operation.") # Add tooltip for the new button


    # --- Layout Methods ---
    def _layout_snapshot_widgets(self):
        """Arranges widgets - trying clear buttons in same cell."""
        self.snapshot_frame.columnconfigure(1, weight=1) # Entry fields expand
        self.snapshot_frame.columnconfigure(2, weight=0) # Browse button fixed size

        # Row 0: Source Directory
        self.snapshot_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=3)
        # Place button IN SAME CELL as entry, aligned right
        self.snapshot_clear_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 2)) # padx pushes it slightly from right edge
        self.snapshot_browse_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)

        # Row 1: Ignores
        self.snapshot_ignore_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_ignore_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=3)
        # Place button IN SAME CELL as entry, aligned right
        self.snapshot_clear_ignore_button.grid(row=1, column=1, sticky=tk.E, padx=(0, 2))
        # Column 2 is now free for this row

        # Row 2: (Placeholder for future Output Format)

        # Row 3: Controls (Generate Button, Checkbox) - Unchanged
        self.snapshot_regenerate_button.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.snapshot_auto_copy_check.grid(row=3, column=1, sticky=tk.W, padx=15, pady=5)

        # Row 4: Action Buttons (Copy, Save) - Unchanged
        self.snapshot_copy_button.grid(row=4, column=1, sticky=tk.E, padx=5, pady=5)
        self.snapshot_save_button.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        # Row 5: Output Text Area - Spans columns 0, 1, 2
        self.snapshot_map_output.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.snapshot_frame.rowconfigure(5, weight=1) # Text area is row 5

        # Row 6: Status Bar - Spans columns 0, 1, 2
        self.snapshot_status_label.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2, padx=5)

    # Modify _layout_scaffold_widgets in app.py

    def _layout_scaffold_widgets(self):
        """Arranges widgets - trying clear button in same cell."""
        self.scaffold_frame.columnconfigure(0, weight=1)

        # Row 0: Input Buttons (Add Clear Map here)
        self.scaffold_input_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        self.scaffold_paste_button.grid(row=0, column=0, padx=5)
        self.scaffold_load_button.grid(row=0, column=1, padx=5)
        self.scaffold_clear_map_button.grid(row=0, column=2, padx=5) # Looks okay here

        # Row 1: Map Input Text Area - Unchanged
        self.scaffold_map_input.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.scaffold_frame.rowconfigure(1, weight=1)

        # Row 2: Configuration Frame (Base Dir, Format)
        self.scaffold_config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        # Use grid inside this frame:
        self.scaffold_config_frame.columnconfigure(1, weight=1) # Let Base Dir Entry expand
        self.scaffold_base_dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.scaffold_base_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        # Place clear button IN SAME CELL as entry, aligned right
        self.scaffold_clear_base_dir_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 6))
        # Adjust subsequent columns
        self.scaffold_browse_base_button.grid(row=0, column=2, sticky=tk.W, padx=(5, 15)) # Increased left pad
        self.scaffold_format_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 2))
        self.scaffold_format_combo.grid(row=0, column=4, sticky=tk.W, padx=2)

        # Row 3: Create Button - Unchanged
        self.scaffold_create_button.grid(row=3, column=0, sticky=tk.E, pady=5, padx=5)

        # Row 4: Status Bar AND Open Folder Button - Unchanged
        self.scaffold_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=2, padx=5)
        self.scaffold_open_folder_button.grid(row=4, column=0, sticky=tk.E, pady=2, padx=5)
        self.scaffold_open_folder_button.grid_remove() # Hide it initially

    # --- Event Handlers / Commands ---

    def _handle_initial_state(self):
        """Sets up the UI based on launch context."""
        initial_status = "Ready" # Default status message base
        active_tab_widget = self.snapshot_frame # Default tab

        if self.initial_mode == 'snapshot' and self.initial_path:
            active_tab_widget = self.snapshot_frame
            self.snapshot_dir_var.set(str(self.initial_path))
            initial_status = f"Ready to generate map for {self.initial_path.name}"
            # Automatically generate map on startup
            self.after(100, self._generate_snapshot) # Use 'after' to allow window to draw first
        elif self.initial_mode == 'scaffold_from_file' and self.initial_path:
            active_tab_widget = self.scaffold_frame
            if self._load_map_from_path(self.initial_path): # Use helper
                 initial_status = f"Loaded map from {self.initial_path.name}"
            else:
                 initial_status = "Error loading initial map file."
        elif self.initial_mode == 'scaffold_here' and self.initial_path:
             active_tab_widget = self.scaffold_frame
             self.scaffold_base_dir_var.set(str(self.initial_path))
             initial_status = f"Ready to create structure in '{self.initial_path.name}'. Paste or load map."

        # Select the correct starting tab
        self.notebook.select(active_tab_widget)
        # Set initial status on the correct tab's status bar
        target_tab_name = 'snapshot' if active_tab_widget == self.snapshot_frame else 'scaffold'
        self._update_status(initial_status, tab=target_tab_name)

    def _update_status(self, message, is_error=False, is_success=False, tab='scaffold'):
        """Helper to update the status label on the specified tab with color."""
        # Remove "Status: " prefix if already present
        if isinstance(message, str) and message.lower().startswith("status: "):
             message = message[len("Status: "):]

        status_var = self.scaffold_status_var if tab == 'scaffold' else self.snapshot_status_var
        status_label = self.scaffold_status_label if tab == 'scaffold' else self.snapshot_status_label

        status_var.set(f"Status: {message}")

        # Determine color
        color = "black" # Default fallback
        try:
            # Try to use system colors first
            style = ttk.Style()
            default_color = style.lookup('TLabel', 'foreground')
            # Note: Standard system error/success colors aren't easily accessible directly
            # We'll use common explicit colors.
            if is_error:
                color = "red"
            elif is_success:
                color = "#008000" # Dark Green
            else:
                 color = default_color if default_color else "black"
        except tk.TclError:
            # Fallback if style system fails
            if is_error: color = "red"
            elif is_success: color = "green"
            else: color = "black"


        try:
             status_label.config(foreground=color)
             self.update_idletasks() # Force UI update
        except tk.TclError:
             pass # Ignore errors if widget doesn't exist anymore (e.g., closing window)

    def _browse_snapshot_dir(self):
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Source Directory")
        if dir_path:
            self.snapshot_dir_var.set(dir_path)
            # Option: Automatically generate map after Browse?
            # self.after(50, self._generate_snapshot)

    def _generate_snapshot(self):
        source_dir = self.snapshot_dir_var.get()
        if not source_dir or not Path(source_dir).is_dir():
            messagebox.showwarning("Input Required", "Please select a valid source directory.")
            self._update_status("Snapshot failed: Invalid source directory.", is_error=True, tab='snapshot')
            return

        custom_ignores_str = self.snapshot_ignore_var.get()
        custom_ignores = set(p.strip() for p in custom_ignores_str.split(',') if p.strip()) if custom_ignores_str else None

        self._update_status("Generating map...", tab='snapshot')
        self.snapshot_map_output.config(state=tk.NORMAL)
        self.snapshot_map_output.delete('1.0', tk.END)
        self.update_idletasks()

        map_result = ""
        try:
            map_result = logic.create_directory_snapshot(source_dir, custom_ignore_patterns=custom_ignores)
            self.snapshot_map_output.insert('1.0', map_result) # Insert result first

            if not map_result.startswith("Error:"):
                status_msg = "Map generated."
                if self.snapshot_auto_copy_var.get():
                    copied_ok = self._copy_snapshot_to_clipboard(show_status=False)
                    status_msg = "Map generated and copied to clipboard." if copied_ok else "Map generated (copy failed)."
                self._update_status(status_msg, is_success=True, tab='snapshot')
            else:
                 self._update_status(map_result, is_error=True, tab='snapshot') # Show error from logic

        except Exception as e:
             error_msg = f"Failed to generate snapshot: {e}"
             messagebox.showerror("Error", error_msg)
             self.snapshot_map_output.insert('1.0', f"Error: {e}") # Show error in text too
             self._update_status(error_msg, is_error=True, tab='snapshot')

        finally:
             self.snapshot_map_output.config(state=tk.DISABLED)


    def _copy_snapshot_to_clipboard(self, show_status=True):
        map_text = self.snapshot_map_output.get('1.0', tk.END).strip()
        status_msg = ""
        is_error = False
        copied = False

        if map_text and not map_text.startswith("Error:"):
            try:
                pyperclip.copy(map_text)
                status_msg = "Map copied to clipboard."
                is_error = False
                is_success = True
                copied = True
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Could not copy to clipboard:\n{e}")
                status_msg = "Failed to copy map to clipboard."
                is_error = True
                is_success = False
        elif not map_text:
             messagebox.showwarning("No Content", "Nothing to copy.")
             status_msg = "Copy failed: No map content."
             is_error = True
        else: # It's an error message
             messagebox.showwarning("Cannot Copy Error", "Cannot copy error message.")
             status_msg = "Copy failed: Cannot copy error message."
             is_error = True

        if show_status:
             self._update_status(status_msg, is_error=is_error, is_success=is_success, tab='snapshot')
        return copied # Return status if needed


    def _save_snapshot_as(self):
        map_text = self.snapshot_map_output.get('1.0', tk.END).strip()
        if not map_text or map_text.startswith("Error:"):
             messagebox.showwarning("No Content", "Nothing to save.")
             self._update_status("Save failed: No map content.", is_error=True, tab='snapshot')
             return

        suggested_filename = "directory_map.txt"
        try:
             # Try to get root name from first line for default filename
             first_line = map_text.splitlines()[0].strip()
             root_name = first_line.rstrip('/') if first_line else ""
             if root_name:
                 suggested_filename = f"{root_name}_map.txt"
        except IndexError:
             pass

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
            self._update_status(f"Base directory set to '{Path(dir_path).name}'.",is_success=True, tab='scaffold') # Indicate browse success
            self._check_scaffold_readiness() # Check if now ready
        # else: User cancelled dialog

    def _check_scaffold_readiness(self):
        """Checks if map input and base directory are set, updates status if ready."""
        # Check if map text area has content (ignoring just whitespace)
        map_ready = bool(self.scaffold_map_input.get('1.0', tk.END).strip())
        # Check if base directory entry has content
        base_dir_ready = bool(self.scaffold_base_dir_var.get())

        # Only update status if BOTH are ready AND the current status isn't already indicating readiness
        # This prevents overwriting specific error messages from previous steps.
        current_status = self.scaffold_status_var.get()
        if map_ready and base_dir_ready and "ready to create" not in current_status.lower() and "error" not in current_status.lower():
            self._update_status("Ready to create structure.", is_success=True, tab='scaffold')
        # If not ready, we leave the status as it was (e.g., "Loaded map...", "Base directory selected...", or an error)

    def _paste_map_input(self):
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                 self.scaffold_map_input.delete('1.0', tk.END)
                 self.scaffold_map_input.insert('1.0', clipboard_content)
                 self._update_status("Pasted map from clipboard.", tab='scaffold')
                 self._check_scaffold_readiness()
            else:
                 self._update_status("Clipboard is empty.", is_success=True, tab='scaffold')
        except Exception as e:
            # Catch potential pyperclip errors (rare)
            messagebox.showerror("Clipboard Error", f"Could not paste from clipboard:\n{e}")
            self._update_status("Failed to paste from clipboard.", is_error=True, tab='scaffold')


    def _load_map_from_path(self, file_path_obj):
        """Helper to load map from a Path object."""
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                map_content = f.read()
            self.scaffold_map_input.delete('1.0', tk.END)
            self.scaffold_map_input.insert('1.0', map_content)
            return True # Success
        except Exception as e:
            messagebox.showerror("File Load Error", f"Could not load map file:\n{file_path_obj.name}\n\n{e}")
            return False # Failure


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
                 self._update_status(f"Error loading map file.", is_error=True, tab='scaffold')
        # else: User cancelled dialog

    def _create_structure(self):
        # --- Start of Method ---
        # 1. Reset path variable and hide the button initially
        self.last_scaffold_path = None
        self.scaffold_open_folder_button.grid_remove() # Ensure button is hidden

        # --- Get Inputs ---
        map_text = self.scaffold_map_input.get('1.0', tk.END).strip()
        # Debug print for raw text (keep or remove as needed)
        # print("-" * 40)
        # print("DEBUG APP: Raw map_text retrieved from ScrolledText:")
        # print(repr(map_text))
        # print("-" * 40)
        base_dir = self.scaffold_base_dir_var.get()
        format_hint = self.scaffold_format_var.get() # Get selected format

        # --- Input Validation ---
        if not map_text:
            messagebox.showwarning("Input Required", "Map input cannot be empty.")
            self._update_status("Scaffold failed: Map input empty.", is_error=True, tab='scaffold')
            return
        if not base_dir or not Path(base_dir).is_dir():
             messagebox.showwarning("Input Required", "Please select a valid base directory.")
             self._update_status("Scaffold failed: Invalid base directory.", is_error=True, tab='scaffold')
             return

        # --- Call Logic ---
        self._update_status("Creating structure...", tab='scaffold') # Neutral status while working

        try:
             # Call the core logic function (pass format_hint later when implemented)
             msg, success = logic.create_structure_from_map(map_text, base_dir) #, format_hint)

             # 3. Update status label with result and color
             self._update_status(msg, is_error=not success, is_success=success, tab='scaffold')

             # 4. On Success ONLY - Store path and show button
             if success:
                 try:
                      # Determine the full path to the root directory that was created
                      created_root_name = map_text.splitlines()[0].strip().rstrip('/')
                      if created_root_name:
                           full_path = Path(base_dir) / created_root_name
                           # Check if it actually exists before enabling button/storing path
                           if full_path.is_dir():
                               self.last_scaffold_path = full_path # Store the valid path
                               self.scaffold_open_folder_button.grid() # Show the button
                               print(f"Debug: Stored scaffold path: {self.last_scaffold_path}") # Optional debug
                           else:
                               # Should not happen if logic succeeded, but handle defensively
                               print(f"Warning: Scaffold reported success, but created path not found: {full_path}")
                               self._update_status(f"{msg} (Warning: Output path not found!)", is_error=True, tab='scaffold')
                      else:
                           # If root name couldn't be determined, maybe just enable opening base_dir? Or do nothing.
                           print("Warning: Could not determine created root folder name from map.")
                           self._update_status(f"{msg} (Warning: Couldn't determine output root name)", is_success=True, tab='scaffold')

                 except Exception as e:
                      # Error during post-success processing (getting path, showing button)
                      print(f"Warning: Error processing success state: {e}")
                      # Update status to reflect success but issue enabling button
                      self._update_status(f"{msg} (Info: Could not enable 'Open Folder' button)", is_success=True, tab='scaffold')
                      self.last_scaffold_path = None # Ensure path is cleared

        except Exception as e:
             # Catch unexpected errors from the logic layer or here
             error_msg = f"Fatal error during creation: {e}"
             self._update_status(error_msg, is_error=True, tab='scaffold')
             messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")

    def _open_last_scaffold_folder(self):
        """Opens the last successfully created scaffold output folder."""
        if not self.last_scaffold_path:
            self._update_status("No scaffold output folder recorded.", is_error=True, tab='scaffold')
            return

        if not self.last_scaffold_path.is_dir():
             self._update_status(f"Output folder not found: {self.last_scaffold_path}", is_error=True, tab='scaffold')
             return

        path_to_open = str(self.last_scaffold_path)
        try:
            print(f"Debug: Attempting to open folder: {path_to_open}") # Debug print
            if sys.platform == "win32":
                os.startfile(path_to_open)
                self._update_status(f"Opened folder: {self.last_scaffold_path.name}", is_success=True, tab='scaffold')
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', path_to_open], check=True)
                self._update_status(f"Opened folder: {self.last_scaffold_path.name}", is_success=True, tab='scaffold')
            else: # Linux and other POSIX variants
                subprocess.run(['xdg-open', path_to_open], check=True)
                self._update_status(f"Opened folder: {self.last_scaffold_path.name}", is_success=True, tab='scaffold')
        except FileNotFoundError:
             # Error if 'open' or 'xdg-open' command doesn't exist
             messagebox.showerror("Error", f"Could not find command to open folder for platform {sys.platform}.")
             self._update_status("Error opening folder: command not found.", is_error=True, tab='scaffold')
        except subprocess.CalledProcessError as e:
             # Error if the command fails
              messagebox.showerror("Error", f"Failed to open folder using system command:\n{e}")
              self._update_status(f"Error opening folder: {e}", is_error=True, tab='scaffold')
        except Exception as e:
            # Catch-all for other errors like permissions
            messagebox.showerror("Error", f"Could not open folder:\n{e}")
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
    # try:
    #     if Path(test_scaffold_path).exists():
    #         shutil.rmtree(test_scaffold_path)
    # except Exception as e:
    #     print(f"Could not clean up test dir: {e}")