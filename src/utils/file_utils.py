import os
import json
from typing import Optional

def get_file_icon(filename):
    """Return appropriate emoji based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    
    # Images
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff', '.webp']:
        return "🖼️", "image"
    
    # Documents
    elif ext in ['.doc', '.docx', '.odt', '.rtf', '.pdf', '.txt', '.md', '.csv', '.xlsx', '.xls', '.pptx', '.ppt']:
        if ext == '.pdf':
            return "📕", "document"
        elif ext in ['.xlsx', '.xls', '.csv']:
            return "📊", "document"
        elif ext in ['.pptx', '.ppt']:
            return "📑", "document"
        elif ext in ['.md', '.txt']:
            return "📝", "document"
        else:
            return "📄", "document"
    
    # Code & Scripts
    elif ext in ['.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.php', '.sh', '.bat', '.ps1', '.rb', '.go', '.ts', '.json', '.xml']:
        if ext == '.py':
            return "🐍", "code"
        elif ext == '.js':
            return "📜", "code"
        elif ext in ['.html', '.css']:
            return "🌐", "code"
        elif ext == '.json' or ext == '.xml':
            return "🔧", "code"
        else:
            return "📜", "code"
    
    # Archives
    elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
        return "🗜️", "archive"
    
    # Audio
    elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
        return "🔊", "file"
    
    # Video
    elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return "🎬", "file"
    
    # Executable
    elif ext in ['.exe', '.app', '.dll', '.so']:
        return "⚙️", "file"
    
    # Default
    else:
        return "📄", "file"

def save_to_downloads(content: str, filename: str) -> str:
    """Save content to the Downloads folder.
    
    Args:
        content: The content to save
        filename: The name of the file
        
    Returns:
        str: The full path where the file was saved
        
    Raises:
        IOError: If the file cannot be saved
    """
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
    with open(downloads_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return downloads_path

def copy_to_clipboard(window, content: str) -> None:
    """Copy content to the system clipboard.
    
    Args:
        window: The Tkinter window instance
        content: The content to copy
    """
    window.clipboard_clear()
    window.clipboard_append(content)
    window.update()

def get_file_extension(format_name: str) -> str:
    """Get the appropriate file extension for a format.
    
    Args:
        format_name: The name of the format
        
    Returns:
        str: The file extension (including the dot)
    """
    extensions = {
        "LLM Output": ".txt",
        "Human Output": ".txt",
        "Diagram Output": ".md"
    }
    return extensions.get(format_name, ".txt") 