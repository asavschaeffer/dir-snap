import tkinter as tk
from tkinter import ttk

class SettingsWindow:
    """Settings window for DirSnap application."""
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("DirSnap Settings")
        self.window.geometry("400x500")
        self.window.resizable(False, False)
        
        # Make the window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Add padding around the content
        self.main_frame = ttk.Frame(self.window, padding="10")
        self.main_frame.pack(fill="both", expand=True)
        
        # Initialize variables
        self.auto_copy_path_var = tk.BooleanVar(value=False)
        self.diagram_type_var = tk.StringVar(value="mindmap")
        self.diagram_orientation_var = tk.StringVar(value="TD")
        self.mermaid_wrap_var = tk.BooleanVar(value=True)
        self.max_depth_var = tk.StringVar(value="3")
        self.max_items_var = tk.StringVar(value="5")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the settings UI components."""
        # Download settings (first, as it affects all outputs)
        download_frame = ttk.LabelFrame(self.main_frame, text="Download Settings", padding="5")
        download_frame.pack(fill="x", pady=5)
        
        # Auto-copy path option
        ttk.Checkbutton(download_frame, text="Copy file path to clipboard after download", 
                       variable=self.auto_copy_path_var).pack(anchor="w", pady=2)
        
        # Diagram settings (main section)
        diagram_frame = ttk.LabelFrame(self.main_frame, text="Diagram Settings", padding="5")
        diagram_frame.pack(fill="x", pady=5)
        
        # Diagram configuration subsection
        config_frame = ttk.LabelFrame(diagram_frame, text="Configuration", padding="5")
        config_frame.pack(fill="x", pady=2)
        
        # Diagram type selection
        ttk.Label(config_frame, text="Diagram Type:").pack(anchor="w")
        diagram_types = ["mindmap", "graph", "flowchart"]
        ttk.OptionMenu(config_frame, self.diagram_type_var, *diagram_types).pack(fill="x", pady=2)
        
        # Diagram orientation (only for graph and flowchart)
        ttk.Label(config_frame, text="Orientation:").pack(anchor="w")
        orientations = ["TD", "LR"]
        ttk.OptionMenu(config_frame, self.diagram_orientation_var, *orientations).pack(fill="x", pady=2)
        
        # Mermaid code block wrapping
        ttk.Checkbutton(config_frame, text="Wrap in ```mermaid code block", 
                       variable=self.mermaid_wrap_var).pack(anchor="w", pady=2)
        
        # Diagram limits subsection
        limits_frame = ttk.LabelFrame(diagram_frame, text="Limits", padding="5")
        limits_frame.pack(fill="x", pady=2)
        
        # Max depth
        depth_frame = ttk.Frame(limits_frame)
        depth_frame.pack(fill="x", pady=2)
        ttk.Label(depth_frame, text="Max Depth:").pack(side="left")
        ttk.Entry(depth_frame, textvariable=self.max_depth_var, width=5).pack(side="left", padx=5)
        
        # Max items per directory
        items_frame = ttk.Frame(limits_frame)
        items_frame.pack(fill="x", pady=2)
        ttk.Label(items_frame, text="Max Items per Directory:").pack(side="left")
        ttk.Entry(items_frame, textvariable=self.max_items_var, width=5).pack(side="left", padx=5)
        
        # Add a separator
        ttk.Separator(self.main_frame, orient="horizontal").pack(fill="x", pady=10)
        
        # Add OK button
        ttk.Button(self.main_frame, text="OK", command=self.window.destroy).pack(pady=5)
    
    def get_settings(self):
        """Get the current settings values."""
        # Construct the full diagram type based on selections
        diagram_type = self.diagram_type_var.get()
        if diagram_type != "mindmap":
            diagram_type = f"{diagram_type} {self.diagram_orientation_var.get()}"
            
        return {
            'auto_copy_path': self.auto_copy_path_var.get(),
            'mermaid_format': diagram_type,
            'mermaid_wrap': self.mermaid_wrap_var.get(),
            'max_depth': int(self.max_depth_var.get()),
            'max_items': int(self.max_items_var.get())
        } 