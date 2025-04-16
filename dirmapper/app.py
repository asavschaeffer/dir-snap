# dirmapper/app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pyperclip # Dependency: pip install pyperclip
from pathlib import Path
import sys
import os # Needed for os.startfile (optional feature)

# Use relative import to access logic.py within the same package
try:
    from . import logic
except ImportError:
    # Fallback for running app.py directly for testing UI (not recommended for final)
    import logic

class DirMapperApp(tk.Tk):
    def __init__(self, initial_path=None, initial_mode='snapshot'):
        super().__init__()

        self.initial_path = Path(initial_path) if initial_path else None
        self.initial_mode = initial_mode

        self.title("Directory Mapper & Scaffolder")
        # Set minimum size
        self.minsize(550, 450)

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

        self.snapshot_ignore_var = tk.StringVar()
        self.snapshot_ignore_entry = ttk.Entry(self.snapshot_frame, textvariable=self.snapshot_ignore_var, width=50)

        # ... inside _create_snapshot_widgets, after creating snapshot_ignore_entry ...

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
        # Maybe: Add Tooltip later using a helper library or custom class
        # self.create_tooltip(self.snapshot_default_ignores_label, "\n".join(sorted(list(logic.DEFAULT_IGNORE_PATTERNS))))

        self.snapshot_regenerate_button = ttk.Button(self.snapshot_frame, text="Generate / Regenerate Map", command=self._generate_snapshot)

        # Checkbox
        self.snapshot_auto_copy_var = tk.BooleanVar(value=False) # Default OFF
        self.snapshot_auto_copy_check = ttk.Checkbutton(self.snapshot_frame, text="Auto-copy on generation", variable=self.snapshot_auto_copy_var)

        # Output Area
        self.snapshot_map_output = scrolledtext.ScrolledText(self.snapshot_frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED) # Read-only

        # Action Buttons
        self.snapshot_copy_button = ttk.Button(self.snapshot_frame, text="Copy to Clipboard", command=self._copy_snapshot_to_clipboard)
        self.snapshot_save_button = ttk.Button(self.snapshot_frame, text="Save Map As...", command=self._save_snapshot_as)

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

        # Config Row Frame (to group base dir and format selector)
        self.scaffold_config_frame = ttk.Frame(self.scaffold_frame)
        # Widgets inside config frame
        self.scaffold_base_dir_label = ttk.Label(self.scaffold_config_frame, text="Base Directory:")
        self.scaffold_base_dir_var = tk.StringVar()
        self.scaffold_base_dir_entry = ttk.Entry(self.scaffold_config_frame, textvariable=self.scaffold_base_dir_var, width=40)
        self.scaffold_browse_base_button = ttk.Button(self.scaffold_config_frame, text="Browse...", command=self._browse_scaffold_base_dir)

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

    # --- Layout Methods ---
    def _layout_snapshot_widgets(self):
        """Arranges widgets in the Snapshot tab including default ignores label."""
        # Configure column weights
        self.snapshot_frame.columnconfigure(1, weight=1) # Let column 1 expand (entries)

        # Row 0: Source Directory
        self.snapshot_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=3)
        self.snapshot_browse_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)

        # Row 1: Custom Ignores Entry
        self.snapshot_ignore_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.snapshot_ignore_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=3) # Span cols 1 and 2

        # Row 2: Default Ignores Info Label <--- NEW ROW
        self.snapshot_default_ignores_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=7, pady=(0, 5)) # Indent slightly under entry

        # Row 3: (Placeholder for future Output Format)

        # Row 4: Controls (Generate Button, Checkbox) <--- Now Row 4
        self.snapshot_regenerate_button.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.snapshot_auto_copy_check.grid(row=4, column=1, sticky=tk.W, padx=15, pady=5)

        # Row 5: Action Buttons (Copy, Save) <--- Now Row 5
        self.snapshot_copy_button.grid(row=5, column=1, sticky=tk.E, padx=5, pady=5)
        self.snapshot_save_button.grid(row=5, column=2, sticky=tk.W, padx=5, pady=5)

        # Row 6: Output Text Area - Spans all 3 columns <--- Now Row 6
        self.snapshot_map_output.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.snapshot_frame.rowconfigure(6, weight=1) # Allow text area (now row 6) to expand vertically

        # Row 7: Status Bar <--- Now Row 7
        self.snapshot_status_label.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2, padx=5)

    
    def _layout_scaffold_widgets(self):
        """Arranges widgets in the Scaffold tab using grid."""
        self.scaffold_frame.columnconfigure(0, weight=1) # Allow text area/config frame to expand

        # Row 0: Input Buttons
        self.scaffold_input_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        # Use grid inside this frame for consistency
        self.scaffold_paste_button.grid(row=0, column=0, padx=5)
        self.scaffold_load_button.grid(row=0, column=1, padx=5)

        # Row 1: Map Input Text Area
        self.scaffold_map_input.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.scaffold_frame.rowconfigure(1, weight=1) # Allow text area to expand vertically

        # Row 2: Configuration Frame (Base Dir, Format)
        self.scaffold_config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        # Use grid inside this frame:
        self.scaffold_config_frame.columnconfigure(1, weight=1) # Let Base Dir Entry expand
        self.scaffold_base_dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.scaffold_base_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        self.scaffold_browse_base_button.grid(row=0, column=2, sticky=tk.W, padx=(2, 15))
        self.scaffold_format_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 2))
        self.scaffold_format_combo.grid(row=0, column=4, sticky=tk.W, padx=2)

        # Row 3: Create Button
        self.scaffold_create_button.grid(row=3, column=0, sticky=tk.E, pady=5, padx=5)

        # Row 4: Status Bar
        self.scaffold_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=2, padx=5)

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

    def _update_status(self, message, is_error=False, tab='scaffold'):
        """Helper to update the status label on the specified tab."""
        # Remove "Status: " prefix if already present
        if message.lower().startswith("status: "):
            message = message[len("Status: "):]

        status_var = self.scaffold_status_var if tab == 'scaffold' else self.snapshot_status_var
        status_label = self.scaffold_status_label if tab == 'scaffold' else self.snapshot_status_label

        status_var.set(f"Status: {message}")
        color = "red" if is_error else "black" # TODO: Use system/theme colors if possible
        try:
             # This might fail if the window is closing
             status_label.config(foreground=color)
             self.update_idletasks() # Force UI update
        except tk.TclError:
             pass # Ignore errors if widget doesn't exist anymore


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
                     self._copy_snapshot_to_clipboard(show_status=False) # Don't show status again
                     status_msg = "Map generated and copied to clipboard."
                self._update_status(status_msg, tab='snapshot')
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
                copied = True
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Could not copy to clipboard:\n{e}")
                status_msg = "Failed to copy map to clipboard."
                is_error = True
        elif not map_text:
             messagebox.showwarning("No Content", "Nothing to copy.")
             status_msg = "Copy failed: No map content."
             is_error = True
        else: # It's an error message
             messagebox.showwarning("Cannot Copy Error", "Cannot copy error message.")
             status_msg = "Copy failed: Cannot copy error message."
             is_error = True

        if show_status:
             self._update_status(status_msg, is_error=is_error, tab='snapshot')
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
                self._update_status(f"Map saved to {saved_filename}", tab='snapshot')
            except Exception as e:
                messagebox.showerror("File Save Error", f"Could not save file:\n{e}")
                self._update_status(f"Failed to save map to {saved_filename}", is_error=True, tab='snapshot')
        else:
             self._update_status("Save cancelled.", tab='snapshot')


    def _browse_scaffold_base_dir(self):
        dir_path = filedialog.askdirectory(mustexist=True, title="Select Base Directory for Scaffolding")
        if dir_path:
            self.scaffold_base_dir_var.set(dir_path)
            self._update_status(f"Base directory set to '{Path(dir_path).name}'.", tab='scaffold') # Indicate browse success
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
            self._update_status("Ready to create structure.", tab='scaffold')
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
                 self._update_status("Clipboard is empty.", tab='scaffold')
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
             if self._load_map_from_path(Path(file_path)):
                 self._update_status(f"Loaded map from {Path(file_path).name}", tab='scaffold')
                 self._check_scaffold_readiness()
             else:
                 self._update_status(f"Error loading map file.", is_error=True, tab='scaffold')
        # else: User cancelled dialog


    def _create_structure(self):
        map_text = self.scaffold_map_input.get('1.0', tk.END).strip()
        print("-" * 40)
        print("DEBUG APP: Raw map_text retrieved from ScrolledText:")
        print(repr(map_text)) # Use repr() to show hidden chars like \r, \n, \t etc.
        print("-" * 40)
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
        self._update_status("Creating structure...", tab='scaffold')

        try:
             # TODO: Update logic.create_structure_from_map later to accept format_hint
             # For now, it ignores the hint in MVP
             msg, success = logic.create_structure_from_map(map_text, base_dir) #, format_hint)
             self._update_status(msg, is_error=not success, tab='scaffold') # Display result from logic

             # Optional: Open explorer on success? (Platform dependent)
             if success and sys.platform == "win32":
                 try:
                      # Attempt to open the PARENT directory containing the new structure
                      # Get the created root name from the first line of the map
                      created_root_name = map_text.splitlines()[0].strip().rstrip('/')
                      full_path = Path(base_dir) / created_root_name
                      os.startfile(full_path.parent) # Open parent
                 except Exception as open_e:
                      print(f"Info: Could not open explorer: {open_e}") # Non-critical error
             # Add similar logic for macOS ('open /path/to/parent') or Linux ('xdg-open /path/to/parent') if desired

        except Exception as e:
             # Catch unexpected errors from the logic layer or here
             error_msg = f"Fatal error during creation: {e}"
             self._update_status(error_msg, is_error=True, tab='scaffold')
             messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")


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