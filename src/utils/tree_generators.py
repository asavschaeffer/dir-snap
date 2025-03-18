import os
import json
import sys
from datetime import datetime

# Add the parent directory to sys.path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.file_utils import get_file_icon

def generate_text_tree(path, indent=''):
    """Generate a minimal text-based tree representation optimized for LLM consumption.
    Format: type|path
    Example: d|/root/folder f|/root/file.txt
    """
    tree = []
    for item in sorted(os.listdir(path)):
        item_path = os.path.join(path, item)
        rel_path = os.path.relpath(item_path, os.path.dirname(path))
        if os.path.isdir(item_path):
            tree.append(f"d|{rel_path}")
            tree.extend(generate_text_tree(item_path, indent + '  '))
        else:
            tree.append(f"f|{rel_path}")
    return tree

def generate_json_tree(path):
    """Generate a human-readable tree representation with emojis and visual elements."""
    tree = []
    root_name = os.path.basename(path)
    tree.append(f"📁 {root_name}")
    
    def add_subtree(current_path, prefix="", is_last=True):
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
    add_subtree(path)
    return "\n".join(tree)

def format_size(size_bytes):
    """Convert size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def generate_mermaid_tree(path):
    """Generate a Mermaid flowchart representing the directory structure with file type icons."""
    tree = "flowchart LR\n"
    tree += "    %% Directory tree for " + os.path.basename(path) + "\n"
    tree += "    classDef folder fill:#f9d094,stroke:#d8a14f,stroke-width:1px;\n"
    tree += "    classDef file fill:#f2f2f2,stroke:#d4d4d4,stroke-width:1px;\n"
    tree += "    classDef image fill:#d4f4dd,stroke:#68c387,stroke-width:1px;\n"
    tree += "    classDef code fill:#d4e7f9,stroke:#4a89dc,stroke-width:1px;\n"
    tree += "    classDef document fill:#f9d4e8,stroke:#de5c9d,stroke-width:1px;\n"
    tree += "    classDef archive fill:#e8d4f9,stroke:#9b59b6,stroke-width:1px;\n"
    
    root_id = "root"
    root_name = os.path.basename(path)
    tree += f"    {root_id}[\"📁 {root_name}\"]\n"
    tree += "    class " + root_id + " folder;\n"
    
    node_counter = [1]
    tree += generate_mermaid_subtree(path, root_id, node_counter)
    return tree

def generate_mermaid_subtree(path, parent_id, node_counter):
    """Generate Mermaid subtree for the given path with file type detection."""
    tree = ''
    for item in sorted(os.listdir(path)):
        item_path = os.path.join(path, item)
        current_id = f"node{node_counter[0]}"
        node_counter[0] += 1
        
        if os.path.isdir(item_path):
            # It's a directory
            tree += f"    {current_id}[\"📁 {item}\"]\n"
            tree += f"    {parent_id} --> {current_id}\n"
            tree += "    class " + current_id + " folder;\n"
            tree += generate_mermaid_subtree(item_path, current_id, node_counter)
        else:
            # It's a file
            icon, file_class = get_file_icon(item)
            tree += f"    {current_id}[\"{icon} {item}\"]\n"
            tree += f"    {parent_id} --> {current_id}\n"
            tree += f"    class {current_id} {file_class};\n"
    return tree 