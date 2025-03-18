import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import sys

# Add the parent directory to sys.path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.ui.tooltip import ToolTip
from src.ui.settings import SettingsWindow
from src.generators import LLMGenerator, HumanGenerator, DiagramGenerator
from src.utils.file_utils import save_to_downloads, copy_to_clipboard, get_file_extension

class DirSnapApp(tk.Tk):
    """
    Main application class for DirSnap - a directory structure visualization tool.
    """
    def __init__(self, initial_directory=None):
        super().__init__()
        self.title("DirSnap")
        self.geometry("700x500")
        
        self.directory = None
        self._setup_ui()
        
        # If an initial directory was provided, load it
        if initial_directory:
            self.load_directory(initial_directory)
        
    def _setup_ui(self):
        """Set up the user interface components."""
        # Step 1 components
        self.dir_status_label = tk.Label(self, text="Step 1: Choose a folder to list its files", fg="green")
        self.dir_status_label.pack(pady=5)
        
        self.select_button = tk.Button(self, text="Choose Root Folder", command=self.select_directory)
        self.select_button.pack(pady=5)
        self.selected_label = tk.Label(self, text="Selected: None (pick your main folder)", fg="gray")
        self.selected_label.pack(pady=5)
        
        # Step 2 components (initially hidden)
        self.format_status_label = tk.Label(self, text="Step 2: Pick a format and use the buttons", fg="green")
        
        # Format description
        format_desc = "LLM Output: Optimized for AI context\nHuman Output: Human-readable directory structure\nDiagram Output: Visual representation"
        self.format_desc_label = tk.Label(self, text=format_desc, fg="gray", justify=tk.LEFT)
        
        self.format_frame = tk.Frame(self)
        self.format_var = tk.StringVar(self)
        self.format_var.set("Human Output")
        tk.Label(self.format_frame, text="Output Format:", font=("Arial", 10)).pack(side=tk.TOP, pady=2)
        self.format_menu = tk.OptionMenu(self.format_frame, self.format_var, 
                                       "LLM Output", "Human Output", "Diagram Output")
        self.format_menu.config(font=("Arial", 10), width=15)
        self.format_menu.pack(side=tk.TOP, pady=2)
        
        # Settings button
        self.settings_button = tk.Button(self.format_frame, text="⚙️", font=("Arial", 12),
                                       command=self.show_settings)
        self.settings_button.pack(side=tk.TOP, pady=2)
        
        self.button_frame = tk.Frame(self)
        self.download_button = tk.Button(self.button_frame, text="↓", font=("Arial", 14), 
                                        command=self.save_to_downloads)
        self.download_label = tk.Label(self.button_frame, text="Save to Downloads", fg="gray")
        self.download_button.pack(side=tk.LEFT, padx=5)
        self.download_label.pack(side=tk.LEFT, padx=5)
        
        self.clipboard_button = tk.Button(self.button_frame, text="📋", font=("Arial", 14), 
                                         command=self.copy_to_clipboard)
        self.clipboard_label = tk.Label(self.button_frame, text="Copy to Clipboard", fg="gray")
        self.clipboard_button.pack(side=tk.LEFT, padx=5)
        self.clipboard_label.pack(side=tk.LEFT, padx=5)
        
        self.text_widget = scrolledtext.ScrolledText(self, width=80, height=20)
        
        # Initialize generators
        self.llm_generator = LLMGenerator()
        self.human_generator = HumanGenerator()
        self.diagram_generator = DiagramGenerator()
        
        # Initialize settings
        self.settings = {
            'mermaid_format': 'mindmap',
            'mermaid_wrap': True,
            'auto_copy_path': False,
            'max_depth': 3,
            'max_items': 5
        }

    def show_settings(self):
        """Show the settings window."""
        settings_window = SettingsWindow(self)
        self.wait_window(settings_window.window)
        self.settings = settings_window.get_settings()

    def select_directory(self):
        """Handle directory selection and UI state changes."""
        directory = filedialog.askdirectory()
        
        # If user cancels or selects nothing
        if not directory:
            # If they had a directory previously selected, reset to Step 1
            if self.directory:
                self.directory = None
                self.selected_label.config(text="Selected: None (pick your main folder)", fg="gray", font=("Arial", 10))
                
                # Hide Step 2 components
                self.format_status_label.pack_forget()
                self.format_desc_label.pack_forget()
                self.format_frame.pack_forget()
                self.button_frame.pack_forget()
                self.text_widget.pack_forget()
                
                # Show Step 1 components again
                self.dir_status_label.pack(pady=5)
                
                # Clear the text widget
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.config(state=tk.DISABLED)
            return
        
        # User selected a directory
        self.directory = directory
        self.selected_label.config(text=f"Selected: {self.directory}", fg="black", font=("Arial", 10, "bold"))
        self.dir_status_label.pack_forget()
        self.format_status_label.pack(pady=5)
        self.format_desc_label.pack(pady=2)
        self.format_frame.pack(pady=5)
        self.button_frame.pack(pady=5)
        self.text_widget.pack(pady=5)

    def generate_output(self):
        """Generate output based on the selected format."""
        if not self.directory:
            return None
            
        format = self.format_var.get()
        if format == "LLM Output":
            return self.llm_generator.generate(self.directory)
        elif format == "Human Output":
            return self.human_generator.generate(self.directory)
        elif format == "Diagram Output":
            output = self.diagram_generator.generate(
                self.directory,
                max_depth=self.settings['max_depth'],
                max_items_per_dir=self.settings['max_items'],
                diagram_type=self.settings['mermaid_format']
            )
            if self.settings['mermaid_wrap']:
                output = "```mermaid\n" + output + "\n```"
            return output

    def save_to_downloads(self):
        """Save the generated output to the Downloads folder."""
        if not self.directory:
            messagebox.showerror("Error", "Please choose a root folder first")
            return
            
        output = self.generate_output()
        if not output:
            messagebox.showerror("Error", "Failed to generate output")
            return
            
        format = self.format_var.get()
        root_name = os.path.basename(self.directory) or "Untitled"
        filename = f"{root_name} File Directory Tree{get_file_extension(format)}"
        
        try:
            downloads_path = save_to_downloads(output, filename)
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(tk.END, output)
            self.text_widget.config(state=tk.DISABLED)
            
            # Auto-copy path if enabled
            if self.settings['auto_copy_path']:
                copy_to_clipboard(self, downloads_path)
                messagebox.showinfo("Success", f"Saved to Downloads as {filename}\nPath copied to clipboard!")
            else:
                messagebox.showinfo("Success", f"Saved to Downloads as {filename}")
                
            self.format_status_label.config(text="Saved! Attach the file to your AI chat", fg="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def copy_to_clipboard(self):
        """Copy the generated output to the clipboard."""
        if not self.directory:
            messagebox.showerror("Error", "Please choose a root folder first")
            return
            
        output = self.generate_output()
        if not output:
            messagebox.showerror("Error", "Failed to generate output")
            return
        
        try:
            copy_to_clipboard(self, output)
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(tk.END, output)
            self.text_widget.config(state=tk.DISABLED)
            messagebox.showinfo("Success", "Copied to clipboard")
            self.format_status_label.config(text="Copied! Paste it into your AI chat", fg="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {str(e)}")

    def load_directory(self, directory_path):
        """Load a directory and update the UI accordingly."""
        if os.path.isdir(directory_path):
            self.directory = directory_path
            self.selected_label.config(text=f"Selected: {self.directory}", fg="black", font=("Arial", 10, "bold"))
            self.dir_status_label.pack_forget()
            self.format_status_label.pack(pady=5)
            self.format_desc_label.pack(pady=2)
            self.format_frame.pack(pady=5)
            self.button_frame.pack(pady=5)
            self.text_widget.pack(pady=5) 