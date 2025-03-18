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

def generate_mermaid_tree(path, max_depth=3, max_items_per_dir=5, diagram_type="mindmap"):
    """Generate a Mermaid diagram representing the directory structure with file type icons.
    Args:
        path: The root directory path
        max_depth: Maximum depth of directories to show (default: 3)
        max_items_per_dir: Maximum number of items to show per directory (default: 5)
        diagram_type: Type of Mermaid diagram to generate (mindmap, graph TD, graph LR, flowchart TD, flowchart LR)
    """
    # Initialize the diagram based on type
    if diagram_type == "mindmap":
        tree = "mindmap\n"
        tree += "  root((📁 " + os.path.basename(path) + "))\n"
        
        def add_subtree(current_path, parent_indent="", current_depth=0):
            if current_depth >= max_depth:
                return parent_indent + "    (⋯)\n"
                
            tree = ""
            items = sorted(os.listdir(current_path))[:max_items_per_dir]
            
            for i, item in enumerate(items):
                item_path = os.path.join(current_path, item)
                is_last = i == len(items) - 1
                
                if os.path.isdir(item_path):
                    # It's a directory
                    icon = "📁"
                    tree += parent_indent + "    (" + icon + " " + item + ")\n"
                    # Recursively add children with increased indentation
                    next_indent = parent_indent + "        " if not is_last else parent_indent + "    "
                    tree += add_subtree(item_path, next_indent, current_depth + 1)
                else:
                    # It's a file
                    icon, _ = get_file_icon(item)
                    tree += parent_indent + "    (" + icon + " " + item + ")\n"
            
            # Add ellipsis if there are more items
            if len(os.listdir(current_path)) > max_items_per_dir:
                tree += parent_indent + "    (⋯)\n"
                
            return tree
        
        # Start the tree from the first level
        tree += add_subtree(path)
        return tree
        
    else:
        # For graph and flowchart types
        tree = f"{diagram_type}\n"
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
        tree += generate_mermaid_subtree(path, root_id, node_counter, 
                                       max_depth=max_depth, max_items_per_dir=max_items_per_dir)
        return tree

def generate_mermaid_subtree(path, parent_id, node_counter, max_depth=3, max_items_per_dir=5, current_depth=0):
    """Generate Mermaid subtree for the given path with file type detection."""
    if current_depth >= max_depth:
        # Add an ellipsis node to indicate more content
        current_id = f"node{node_counter[0]}"
        node_counter[0] += 1
        tree = f"    {current_id}[\"⋯\"]\n"
        tree += f"    {parent_id} --> {current_id}\n"
        tree += f"    class {current_id} file;\n"
        return tree

    tree = ''
    items = sorted(os.listdir(path))[:max_items_per_dir]  # Limit items per directory
    
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        current_id = f"node{node_counter[0]}"
        node_counter[0] += 1
        
        if os.path.isdir(item_path):
            # It's a directory
            tree += f"    {current_id}[\"📁 {item}\"]\n"
            tree += f"    {parent_id} --> {current_id}\n"
            tree += "    class " + current_id + " folder;\n"
            tree += generate_mermaid_subtree(item_path, current_id, node_counter, 
                                           max_depth=max_depth, max_items_per_dir=max_items_per_dir,
                                           current_depth=current_depth + 1)
        else:
            # It's a file
            icon, file_class = get_file_icon(item)
            tree += f"    {current_id}[\"{icon} {item}\"]\n"
            tree += f"    {parent_id} --> {current_id}\n"
            tree += f"    class {current_id} {file_class};\n"
    
    # If there are more items than max_items_per_dir, add an ellipsis
    if len(os.listdir(path)) > max_items_per_dir:
        current_id = f"node{node_counter[0]}"
        node_counter[0] += 1
        tree += f"    {current_id}[\"⋯\"]\n"
        tree += f"    {parent_id} --> {current_id}\n"
        tree += f"    class {current_id} file;\n"
    
    return tree 