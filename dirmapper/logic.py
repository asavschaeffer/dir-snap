# dirmapper/logic.py

import os
import fnmatch
import re # Keep for potential future use
from pathlib import Path
import shutil # Added for potential cleanup in testing block

# --- Default Configuration ---
DEFAULT_IGNORE_PATTERNS = {
    '.git', '.vscode', '__pycache__', 'node_modules', '.DS_Store',
    'build', 'dist', '*.pyc', '*.egg-info', '*.log', '.env',
    # Common backup/temp file patterns
    '*~', '*.tmp', '*.bak', '*.swp',
}
SPACES_PER_LEVEL = 2 # Define the indentation for snapshot output/parsing

# --- Snapshot Function (Fixed Version) ---

def create_directory_snapshot(root_dir_str, custom_ignore_patterns=None):
    """
    Generates an indented text map of a directory structure (MVP format).

    Builds an intermediate tree using os.walk for efficiency and pruning,
    then generates the map string from the tree for correct indentation.

    Args:
        root_dir_str (str): The path to the root directory to map.
        custom_ignore_patterns (set, optional): A set of custom patterns to ignore.

    Returns:
        str: The formatted directory map string, or an error message.
    """
    root_dir = Path(root_dir_str).resolve()
    if not root_dir.is_dir():
        return f"Error: Path is not a valid directory: {root_dir_str}"

    ignore_set = DEFAULT_IGNORE_PATTERNS.copy()
    if custom_ignore_patterns:
        ignore_set.update(custom_ignore_patterns)

    try:
        # --- Build Intermediate Tree using os.walk ---
        tree = {'name': root_dir.name, 'is_dir': True, 'children': [], 'path': root_dir}
        node_map = {root_dir: tree} # Map paths to tree nodes

        for root, dirs, files in os.walk(str(root_dir), topdown=True, onerror=None):
            current_path = Path(root).resolve()
            parent_node = node_map.get(current_path)

            if parent_node is None:
                # This path might have been pruned or is inaccessible, skip processing its children
                # Clear dirs to prevent os.walk from trying to descend further into this unknown path
                # print(f"Debug: Skipping path not found in node_map: {current_path}") # Optional debug
                dirs[:] = []
                continue

            # --- Pruning ---
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore_set)]
            files = sorted([f for f in files if not any(fnmatch.fnmatch(f, pattern) for pattern in ignore_set)])
            dirs.sort()

            # Add directories as children
            for d_name in dirs:
                dir_path = current_path / d_name
                child_node = {'name': d_name, 'is_dir': True, 'children': [], 'path': dir_path}
                parent_node['children'].append(child_node)
                node_map[dir_path] = child_node

            # Add files as children
            for f_name in files:
                 child_node = {'name': f_name, 'is_dir': False, 'path': current_path / f_name}
                 parent_node['children'].append(child_node)

        # --- Generate map string from the completed tree ---
        map_lines = []
        def build_map_lines_from_tree(node, level):
            indent = " " * (level * SPACES_PER_LEVEL)
            suffix = "/" if node['is_dir'] else ""
            map_lines.append(f"{indent}{node['name']}{suffix}")

            if node['is_dir']:
                 sorted_children = sorted(node.get('children', []), key=lambda x: (not x['is_dir'], x['name'].lower()))
                 for child in sorted_children:
                     build_map_lines_from_tree(child, level + 1)

        build_map_lines_from_tree(tree, 0) # Start map generation from root node

        return "\n".join(map_lines)

    except Exception as e:
        # Adding more specific error context if possible
        return f"Error during directory processing near {current_path if 'current_path' in locals() else root_dir}: {e}"


# --- Scaffold Functions (MVP: Parses only the format above) ---

def _parse_indent_based_mvp(map_text):
    """
    Parses map text assuming SPACES_PER_LEVEL indentation and trailing '/' for dirs.
    (Internal helper for MVP).

    Returns:
        list[tuple[int, str, bool]]: List of (level, item_name, is_directory), or None if error/empty.
    """
    lines = map_text.strip().splitlines()
    if not lines: return None

    parsed_items = []

    for line_num, line in enumerate(lines):
        line_strip = line.lstrip(' ')
        if not line.strip(): continue # Skip blank lines

        leading_spaces = len(line) - len(line_strip)
        item_name_part = line.strip()

        # Basic validation of indentation
        if leading_spaces % SPACES_PER_LEVEL != 0:
            # Allow level 0 items (no leading space)
            if leading_spaces == 0 and line_num == 0:
                 pass # Allow root item with no indent
            else:
                print(f"Warning: Skipping line {line_num+1} due to inconsistent indentation (not multiple of {SPACES_PER_LEVEL}). Line: '{line}'")
                continue # Skip line in MVP

        level = leading_spaces // SPACES_PER_LEVEL

        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name: continue

        parsed_items.append((level, item_name, is_directory))

    return parsed_items


# Replace ONLY this function in dirmapper/logic.py

def create_structure_from_parsed(parsed_items, base_dir_str):
    """
    Creates directory structure from a list of parsed items.
    (Generic function, takes output from any parser) - Revised Stack Logic

    Args:
        parsed_items (list): List of (level, item_name, is_directory).
        base_dir_str (str): Path to the base directory.

    Returns:
        tuple[str, bool]: (message, success_status).
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir(): return f"Error: Base directory '{base_dir_str}' is not valid.", False
    if not parsed_items: return "Error: No items parsed from map.", False

    # path_stack[N] will hold the Path object for the parent at level N-1
    # So, path_stack[0] = base_dir (parent for level 0 items)
    # path_stack[1] = root_dir (parent for level 1 items) etc.
    path_stack = [base_dir]
    created_root_name = "structure" # Default message name

    try:
        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
            # --- Adjust stack depth BEFORE processing item ---
            # Target stack length should be current_level + 1
            # (e.g., for level 0 item, stack length is 1 [base_dir]; for level 1, length is 2 [base_dir, root_dir])
            while len(path_stack) > current_level + 1:
                path_stack.pop()

            # --- Check for inconsistencies ---
            # After popping, stack length must match the expected parent level + 1
            if len(path_stack) != current_level + 1:
                # This implies the map tried to jump a level down (e.g. level 0 then level 2)
                # Or something went wrong with stack logic before.
                raise ValueError(f"Cannot determine parent directory for item '{item_name}' at level {current_level}. Check map structure/indentation.")

            # The correct parent path is now always the last element in the adjusted stack
            current_parent_path = path_stack[-1]
            current_path = current_parent_path / item_name

            # Store root name for success message
            if i == 0:
                 created_root_name = item_name
                 if not is_directory: raise ValueError("Map must start with a directory.") # Validate root is dir

            # --- Create item ---
            if is_directory:
                current_path.mkdir(parents=True, exist_ok=True)
                # Add this new directory to the stack, making it the parent for the next deeper level
                path_stack.append(current_path)
            else: # Is file
                # Ensure parent exists (should normally, but safety check)
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.touch(exist_ok=True)
                # Files do not extend the stack; the parent for the next item
                # at this level or shallower remains the same directory.

    except ValueError as ve: return f"Error processing structure: {ve}", False
    except Exception as e: return f"Error creating structure for item '{item_name}': {e}", False

    return f"Structure for '{created_root_name}' successfully created in '{base_dir}'", True

def create_structure_from_map(map_text, base_dir_str, format_hint="MVP"):
    """
    Main scaffolding function (MVP version).

    Args:
        map_text (str): The directory map text.
        base_dir_str (str): The path to the base directory.
        format_hint (str, optional): Ignored in MVP, assumes format matching snapshotter.

    Returns:
        tuple[str, bool]: (message, success_status).
    """
    try:
        # In MVP, directly call the specific parser we expect
        parsed_items = _parse_indent_based_mvp(map_text)
        if parsed_items is None:
            return "Error: Failed to parse map text (check warnings?).", False

        return create_structure_from_parsed(parsed_items, base_dir_str)
    except Exception as e:
        return f"Fatal error during scaffolding: {e}", False

# --- Example Usage / Test Harness ---
if __name__ == '__main__':
    print("--- Testing Directory Mapper Logic (v3 - Complete Logic) ---") # Indicate version

    # --- Setup Test Environment ---
    test_root = Path("./_mapper_test_env")
    if test_root.exists():
        print(f"Cleaning up previous test env: {test_root}")
        shutil.rmtree(test_root)
    test_root.mkdir()

    source_dir = test_root / "my_source_project"
    source_dir.mkdir()
    (source_dir / "README.md").touch()
    (source_dir / ".env").touch() # Should be ignored
    src_sub = source_dir / "src"
    src_sub.mkdir()
    (src_sub / "__init__.py").touch()
    (src_sub / "main.py").touch()
    (src_sub / "utils.py").touch()
    data_sub = source_dir / "data"
    data_sub.mkdir()
    (data_sub / "input.csv").touch()
    node_mod = source_dir / "node_modules" # Should be ignored
    node_mod.mkdir()
    (node_mod / "some_lib.js").touch()

    print(f"\n1. Test Source Directory Structure Created in: {source_dir}")

    # --- Test Snapshot ---
    print("\n2. Testing Snapshot Function...")
    snapshot_output = create_directory_snapshot(str(source_dir))
    print("Snapshot Result:")
    print(snapshot_output)
    print("-" * 20)

    # --- Test Scaffold ---
    print("\n3. Testing Scaffold Function...")
    scaffold_target_dir = test_root / "scaffold_output"
    scaffold_target_dir.mkdir() # Base directory

    if snapshot_output.startswith("Error:"):
         print("Snapshot failed, skipping scaffold test.")
    else:
        # *** This is the line that failed before ***
        msg, success = create_structure_from_map(snapshot_output, str(scaffold_target_dir))
        print(f"Scaffold Result: {success} - {msg}")

        # Basic Verification
        created_root_name = None
        if snapshot_output and not snapshot_output.startswith("Error:"):
             first_line = snapshot_output.splitlines()[0].strip()
             if first_line:
                 created_root_name = first_line.rstrip('/')

        if created_root_name:
            created_root_path = scaffold_target_dir / created_root_name
            if success and created_root_path.exists() and created_root_path.is_dir():
                 print(f"Verification: Root folder '{created_root_path.name}' created successfully.")
                 print(f"--> Please manually verify the contents of: {scaffold_target_dir}")
            elif success:
                 print(f"Verification Warning: Scaffolding reported success, but root folder '{created_root_path.name}' not found as expected.")
            else:
                 print("Verification: Scaffolding failed.")
        elif success:
             print("Verification Warning: Scaffolding reported success, but could not determine created root folder name from snapshot.")
        else:
            print("Verification: Scaffolding failed.")


    print("\n--- Testing Complete ---")
    # Keep test environment for inspection:
    print(f"\nTest environment left in: {test_root}")
    # Optional auto-cleanup:
    # input("Press Enter to clean up test environment...")
    # shutil.rmtree(test_root)