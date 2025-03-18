import os
import json
from .base import BaseGenerator

def get_file_icon(filename: str) -> tuple[str, str]:
    """Get the appropriate icon and type for a file."""
    ext = os.path.splitext(filename)[1].lower()
    if os.path.isdir(filename):
        return "📁", "directory"
    elif ext in ['.py']:
        return "🐍", "python"
    elif ext in ['.js', '.jsx', '.ts', '.tsx']:
        return "⚛️", "javascript"
    elif ext in ['.html', '.htm']:
        return "🌐", "html"
    elif ext in ['.css', '.scss', '.sass']:
        return "🎨", "css"
    elif ext in ['.md', '.markdown']:
        return "📝", "markdown"
    elif ext in ['.json']:
        return "📦", "json"
    elif ext in ['.txt']:
        return "📄", "text"
    elif ext in ['.pdf']:
        return "📚", "pdf"
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
        return "🖼️", "image"
    elif ext in ['.mp4', '.avi', '.mov']:
        return "🎥", "video"
    elif ext in ['.mp3', '.wav', '.ogg']:
        return "🎵", "audio"
    elif ext in ['.zip', '.rar', '.7z']:
        return "📦", "archive"
    elif ext in ['.exe', '.app']:
        return "⚙️", "executable"
    else:
        return "📄", "file"

class HumanGenerator(BaseGenerator):
    """Generator for human-readable tree representation."""
    
    def generate(self, directory: str, **kwargs) -> str:
        """Generate a human-readable tree representation with emojis and visual elements.
        
        Args:
            directory: The root directory path
            **kwargs: Not used in this generator
            
        Returns:
            str: The generated human-readable representation
        """
        tree = []
        root_name = os.path.basename(directory)
        tree.append(f"📁 {root_name}")
        
        def add_subtree(current_path: str, prefix: str = "", is_last: bool = True) -> None:
            """Recursively add items to the tree with visual elements."""
            items = sorted(os.listdir(current_path))
            for i, item in enumerate(items):
                item_path = os.path.join(current_path, item)
                is_last_item = i == len(items) - 1
                
                # Create the visual prefix
                visual_prefix = prefix + ("└── " if is_last_item else "├── ")
                
                if os.path.isdir(item_path):
                    # It's a directory
                    icon, _ = get_file_icon(item)
                    tree.append(f"{visual_prefix}{icon} {item}")
                    # Update prefix for next level
                    next_prefix = prefix + ("    " if is_last_item else "│   ")
                    add_subtree(item_path, next_prefix, is_last_item)
                else:
                    # It's a file
                    icon, _ = get_file_icon(item)
                    tree.append(f"{visual_prefix}{icon} {item}")
        
        # Start the tree from the first level of children
        add_subtree(directory)
        return "\n".join(tree) 