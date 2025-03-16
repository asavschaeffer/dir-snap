import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import json
import getpass

class ToolTip:
    def __init__(self, widget, text=None, text_func=None):
        self.widget = widget
        self.text = text
        self.text_func = text_func
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tip_window:
            return
        text = self.text_func() if self.text_func else self.text
        if not text:
            return
        x, y = self.widget.winfo_rootx() + 25, self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=text, justify=tk.LEFT, 
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_tip(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class DirSnapApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DirSnap")
        self.geometry("700x500")
        
        self.dir_status_label = tk.Label(self, text="Step 1: Choose a folder to list its files", fg="green")
        self.dir_status_label.pack(pady=5)
        
        self.select_button = tk.Button(self, text="Choose Root Folder", command=self.select_directory)
        self.select_button.pack(pady=5)
        self.selected_label = tk.Label(self, text="Selected: None (pick your main folder)", fg="gray")
        self.selected_label.pack(pady=5)
        self.directory = None
        
        self.format_status_label = tk.Label(self, text="Step 2: Pick a format and use the buttons", fg="green")
        
        self.format_frame = tk.Frame(self)
        self.format_var = tk.StringVar(self)
        self.format_var.set("Text List")
        tk.Label(self.format_frame, text="Output Format:", font=("Arial", 10)).pack(side=tk.TOP, pady=2)
        self.format_menu = tk.OptionMenu(self.format_frame, self.format_var, "Text List", "JSON", "Mermaid")
        self.format_menu.config(font=("Arial", 10), width=10)
        self.format_menu.pack(side=tk.TOP, pady=2)
        ToolTip(self.format_menu, text="Text List: Best for LLMs\nJSON: Best for humans\nMermaid: Best visually")
        
        self.button_frame = tk.Frame(self)
        self.download_button = tk.Button(self.button_frame, text="↓", font=("Arial", 14), 
                                        command=self.save_to_downloads)
        ToolTip(self.download_button, text_func=lambda: f"Save as {self.format_var.get()} file to Downloads")
        self.download_button.pack(side=tk.LEFT, padx=5)
        self.clipboard_button = tk.Button(self.button_frame, text="📋", font=("Arial", 14), 
                                         command=self.copy_to_clipboard)
        ToolTip(self.clipboard_button, text="Copy directory snap to clipboard")
        self.clipboard_button.pack(side=tk.LEFT, padx=5)
        
        self.text_widget = scrolledtext.ScrolledText(self, width=80, height=20)

    def select_directory(self):
        self.directory = filedialog.askdirectory()
        if self.directory:
            self.selected_label.config(text=f"Selected: {self.directory}", fg="black", font=("Arial", 10, "bold"))
            self.dir_status_label.pack_forget()
            self.format_status_label.pack(pady=5)
            self.format_frame.pack(pady=5)
            self.button_frame.pack(pady=5)
            self.text_widget.pack(pady=5)
        else:
            self.selected_label.config(text="Selected: None (pick your main folder)", fg="gray", font=("Arial", 10))

    def generate_output(self):
        format = self.format_var.get()
        if format == "Text List":
            return self._generate_text_tree(self.directory)
        elif format == "JSON":
            return json.dumps(self._generate_json_tree(self.directory), indent=2)
        elif format == "Mermaid":
            return self._generate_mermaid_tree(self.directory)

    def _generate_text_tree(self, path, indent=''):
        tree = ''
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                tree += f"{indent}{item}/\n"
                tree += self._generate_text_tree(item_path, indent + '  ')
            else:
                tree += f"{indent}{item}\n"
        return tree

    def _generate_json_tree(self, path):
        tree = {"path": path, "contents": []}
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                subtree = self._generate_json_tree(item_path)
                tree["contents"].append(subtree)
            else:
                tree["contents"].append({"name": item})
        return tree

    def _generate_mermaid_tree(self, path):
        tree = "graph TD\n"
        root_id = "A"
        tree += f"{root_id}[{os.path.basename(path)}]\n"
        node_counter = [1]
        tree += self._generate_mermaid_subtree(path, root_id, node_counter)
        return tree

    def _generate_mermaid_subtree(self, path, parent_id, node_counter):
        tree = ''
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            current_id = f"N{node_counter[0]}"
            node_counter[0] += 1
            if os.path.isdir(item_path):
                tree += f"{current_id}[{item}]\n"
                tree += f"{parent_id} --> {current_id}\n"
                tree += self._generate_mermaid_subtree(item_path, current_id, node_counter)
            else:
                tree += f"{current_id}[{item}]\n"
                tree += f"{parent_id} --> {current_id}\n"
        return tree

    def save_to_downloads(self):
        if not self.directory:
            messagebox.showerror("Error", "Please choose a root folder first")
            return
        format = self.format_var.get()
        exts = {"Text List": ".txt", "JSON": ".json", "Mermaid": ".md"}
        root_name = os.path.basename(self.directory) or "Untitled"
        filename = f"{root_name} File Directory Tree{exts[format]}"
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
        
        output = self.generate_output()
        with open(downloads_path, 'w') as f:
            f.write(output)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, output)
        self.text_widget.config(state=tk.DISABLED)
        messagebox.showinfo("Success", f"Saved to Downloads as {filename}")
        self.format_status_label.config(text="Saved! Attach the file to your AI chat", fg="green")

    def copy_to_clipboard(self):
        if not self.directory:
            messagebox.showerror("Error", "Please choose a root folder first")
            return
        output = self.generate_output()
        if not output:
            print("Debug: Output is empty")
            messagebox.showwarning("Warning", "Nothing to copy")
            return
        
        print(f"Debug: Generated output (first 100 chars): {output[:100]}")
        try:
            self.clipboard_clear()
            print("Debug: Clipboard cleared")
            self.clipboard_append(output)
            print("Debug: Output appended to clipboard")
            self.update()
            print("Debug: Tkinter event loop updated")
        except Exception as e:
            print(f"Debug: Clipboard error: {str(e)}")
            messagebox.showerror("Error", f"Failed to copy: {str(e)}")
            return
        
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, output)
        self.text_widget.config(state=tk.DISABLED)
        print("Debug: Text widget updated")
        messagebox.showinfo("Success", "Copied to clipboard")
        self.format_status_label.config(text="Copied! Paste it into your AI chat", fg="green")
        print("Debug: Copy to clipboard completed")

if __name__ == "__main__":
    app = DirSnapApp()
    app.mainloop()