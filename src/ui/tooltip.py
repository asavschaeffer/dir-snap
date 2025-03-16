import tkinter as tk

class ToolTip:
    """
    Creates a tooltip for a given widget.
    """
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