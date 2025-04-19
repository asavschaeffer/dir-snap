import os
import fnmatch
import re
from pathlib import Path
import shutil

# --- Default Configuration ---
DEFAULT_IGNORE_PATTERNS = {
    '.git', '.vscode', '__pycache__', 'node_modules', '.DS_Store',
    'build', 'dist', '*.pyc', '*.egg-info', '*.log', '.env',
    '*~', '*.tmp', '*.bak', '*.swp',
}
DEFAULT_SNAPSHOT_SPACES = 2

# Characters commonly found in tree prefixes (Unicode, ASCII, spaces, tabs)
TREE_PREFIX_CHARS_TO_STRIP = "│├└─| L\\_+-`" + " " + "\t"

# Regex to strip common list/tree prefixes AFTER leading spaces (for Generic parser)
PREFIX_STRIP_RE_GENERIC = re.compile(r"^[ *\-\>`]+")

# Regex to detect tree prefixes more reliably after leading whitespace
TREE_PREFIX_RE = re.compile(r"^\s*([││]|├──|└──)")

# --- Snapshot Function ---

def create_directory_snapshot(root_dir_str, custom_ignore_patterns=None,user_default_ignores=None):
    """
    Generates an indented text map of a directory structure.
    Merges built-in, user-defined default, and custom session ignores.

    Args:
        root_dir_str (str): The path to the root directory to map.
        custom_ignore_patterns (set, optional): A set of custom patterns for this specific run.
        user_default_ignores (list or set, optional): User-defined patterns to always ignore.

    Returns:
        str: The formatted directory map string, or an error message.
    """
    root_dir = Path(root_dir_str).resolve()
    if not root_dir.is_dir():
        return f"Error: Path is not a valid directory: {root_dir_str}"

    ignore_set = DEFAULT_IGNORE_PATTERNS.copy()
    if user_default_ignores:
        # Ensure it's a set and update
        ignore_set.update(set(user_default_ignores))
    if custom_ignore_patterns:
        ignore_set.update(custom_ignore_patterns)

    try:
        # Build Intermediate Tree using os.walk
        tree = {'name': root_dir.name, 'is_dir': True, 'children': [], 'path': root_dir}
        node_map = {root_dir: tree} # Map paths to tree nodes

        for root, dirs, files in os.walk(str(root_dir), topdown=True, onerror=None):
            current_path = Path(root).resolve()
            parent_node = node_map.get(current_path)


            if parent_node is None:
                dirs[:] = [] # Don't descend further if parent node wasn't tracked
                continue

            # Pruning
            dirs_to_keep = []
            for d in dirs:
                # Check if the directory name 'd' matches any pattern in ignore_set
                # Also check if it matches a pattern with a potential trailing slash removed
                is_ignored = False
                for pattern in ignore_set:
                    # Check direct match OR if pattern ends with slash and matches when slash is removed
                    if fnmatch.fnmatch(d, pattern) or \
                        (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(d, pattern.rstrip('/\\'))):
                        is_ignored = True
                        break # Found a matching pattern, stop checking for this directory
                if not is_ignored:
                    dirs_to_keep.append(d)
            dirs[:] = dirs_to_keep # Update dirs with the filtered list        
            files = sorted([f for f in files if not any(fnmatch.fnmatch(f, pattern) for pattern in ignore_set)])
            dirs.sort()

            # Add children to tree
            for d_name in dirs:
                dir_path = current_path / d_name
                child_node = {'name': d_name, 'is_dir': True, 'children': [], 'path': dir_path}
                parent_node['children'].append(child_node)
                node_map[dir_path] = child_node
            for f_name in files:
                 child_node = {'name': f_name, 'is_dir': False, 'path': current_path / f_name}
                 parent_node['children'].append(child_node)

        # Generate map string from the completed tree
        map_lines = []
        def build_map_lines_from_tree(node, level):
            indent = " " * (level * DEFAULT_SNAPSHOT_SPACES)
            suffix = "/" if node['is_dir'] else ""
            map_lines.append(f"{indent}{node['name']}{suffix}")
            if node['is_dir']:
                 sorted_children = sorted(node.get('children', []), key=lambda x: (not x['is_dir'], x['name'].lower()))
                 for child in sorted_children:
                     build_map_lines_from_tree(child, level + 1)

        build_map_lines_from_tree(tree, 0)
        return "\n".join(map_lines)

    except Exception as e:
        # Log unexpected errors during snapshotting
        print(f"ERROR: Exception during directory snapshot near {current_path if 'current_path' in locals() else root_dir}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error during directory processing: {e}"


# ============================================================
# --- Scaffold Functions (Refactored for Multi-Format) ---
# ============================================================

# --- Main Public Function ---

def create_structure_from_map(map_text, base_dir_str, format_hint="Auto-Detect", excluded_lines=None, queue=None):
    """
    Main scaffolding function. Parses map text based on format hint
    and creates the directory structure. Skips lines specified in excluded_lines.
    """
    parsed_items = None
    error_msg = None
    # Initialize excluded_lines if None
    if excluded_lines is None:
        excluded_lines = set()

    try:
        # MODIFIED: Pass excluded_lines to parse_map
        parsed_items = parse_map(map_text, format_hint, excluded_lines=excluded_lines)
        if parsed_items is None or not parsed_items:
             # Handle cases where parsing fails OR *all* lines were excluded
             # Check if the original map had content but everything was excluded
             if map_text.strip() and not parsed_items:
                  error_msg = "Parsing resulted in no items (all lines might be excluded or format error)."
             elif not map_text.strip():
                  error_msg = "Map input is empty."
             else: # Generic parse failure
                  error_msg = "Failed to parse map text (format error?). Check console warnings."
    except Exception as parse_e:
        error_msg = f"Error during map parsing: {parse_e}"
        print(f"ERROR: Exception during map parsing: {parse_e}")
        import traceback
        traceback.print_exc()

    if error_msg:
         return error_msg, False

    # Call the structure creation function (create_structure_from_parsed doesn't need modification)
    try:
        return create_structure_from_parsed(parsed_items, base_dir_str, queue=queue)
    except Exception as create_e:
        # ... (error handling remains the same) ...
        print(f"ERROR: Exception during structure creation: {create_e}")
        import traceback
        traceback.print_exc()
        return f"Fatal error during structure creation: {create_e}", False

# --- Parsing Orchestrator ---

def parse_map(map_text, format_hint, excluded_lines=None):
    """
    Orchestrates parsing based on format hint or auto-detection.
    Skips lines specified in excluded_lines.
    Returns parsed items list or None on failure.
    """
    # Initialize excluded_lines if None
    if excluded_lines is None:
        excluded_lines = set()

    actual_format = format_hint
    if format_hint == "Auto-Detect" or format_hint == "MVP Format": # Treat MVP as needing detection too
        actual_format = _detect_format(map_text)
        print(f"Info: Auto-detected format as: '{actual_format}'")

    # MODIFIED: Pass excluded_lines to specific parsers
    if actual_format == "Spaces (2)":
        return _parse_indent_based(map_text, spaces_per_level=2, excluded_lines=excluded_lines)
    elif actual_format == "Spaces (4)":
        return _parse_indent_based(map_text, spaces_per_level=4, excluded_lines=excluded_lines)
    elif actual_format == "Tabs":
        return _parse_indent_based(map_text, use_tabs=True, excluded_lines=excluded_lines)
    elif actual_format == "Tree":
        return _parse_tree_format(map_text, excluded_lines=excluded_lines)
    elif actual_format == "Generic":
        print("Info: Using generic indentation parser as fallback.")
        return _parse_generic_indent(map_text, excluded_lines=excluded_lines)
    else: # Should not happen if hint comes from Combobox
        print(f"Warning: Unknown format hint '{actual_format}', attempting generic parse.")
        return _parse_generic_indent(map_text, excluded_lines=excluded_lines)


# --- Format Detection Helper ---

def _detect_format(map_text, sample_lines=20):
    """
    Analyzes the first few lines of map_text to detect the format.
    """
    lines = map_text.strip().splitlines()
    non_empty_lines = [line for line in lines if line.strip()][:sample_lines]
    if not non_empty_lines: return "Generic"

    # 1. Check for Tree Prefixes
    if any(TREE_PREFIX_RE.match(line) for line in non_empty_lines[1:]):
        # print("Debug: Detected tree characters.") # Optional debug
        return "Tree"

    # 2. Check for Tabs
    indented_lines = [line for line in non_empty_lines if line and not line.isspace() and line[0] in ('\t', ' ')]
    if any(line.startswith('\t') for line in indented_lines):
        # print("Debug: Detected leading tabs.") # Optional debug
        return "Tabs"

    # 3. Check for Spaces
    leading_spaces = [len(line) - len(line.lstrip(' ')) for line in indented_lines if line.startswith(' ')]
    space_indents = sorted(list(set(sp for sp in leading_spaces if sp > 0)))

    if not space_indents:
        if any(line.startswith(' ') for line in non_empty_lines):
             # print("Debug: Detected spaces but unclear indent level, assuming Spaces (2).") # Optional debug
             return "Spaces (2)"
        else:
             # print("Debug: No clear indentation detected.") # Optional debug
             return "Generic"

    # Analyze differences
    indent_diffs = {space_indents[i] - space_indents[i-1] for i in range(1, len(space_indents))}
    if len(indent_diffs) == 1:
         diff = indent_diffs.pop()
         if space_indents[0] % diff == 0:
             if diff == 4:
                 # print("Debug: Detected consistent space indentation (multiples of 4).") # Optional debug
                 return "Spaces (4)"
             elif diff == 2:
                 # print("Debug: Detected consistent space indentation (multiples of 2).") # Optional debug
                 return "Spaces (2)"
             else:
                 # print(f"Debug: Detected consistent space indentation (multiples of {diff}), using Generic.") # Optional debug
                 return "Generic"

    # print("Debug: Inconsistent space indentation increments detected.") # Optional debug
    return "Generic"

# --- Specific Parser Implementations ---

def _parse_indent_based(map_text, spaces_per_level=None, use_tabs=False, excluded_lines=None):
    """
    Parses map text using consistent space or tab indentation. (Cleaned)
    Skips lines specified in excluded_lines.
    """
    if excluded_lines is None: excluded_lines = set() # Ensure it's a set
    print(f"DEBUG _parse_indent_based: Received excluded_lines = {excluded_lines}") # Optional: See set on entry
    if not (spaces_per_level or use_tabs):
        print("Error (_parse_indent_based): Specify spaces_per_level or use_tabs.")
        return None
    lines = map_text.strip().splitlines()
    if not lines: return None

    parsed_items = []
    indent_char = '\t' if use_tabs else ' '
    indent_unit = 1 if use_tabs else spaces_per_level
    if indent_unit <= 0:
        print("Error (_parse_indent_based): Indent unit must be positive.")
        return None

    for line_num, line in enumerate(lines, start=1):
        if line_num in excluded_lines:
            continue

        if not line.strip(): continue # Skip blank lines

        leading_chars_count = len(line) - len(line.lstrip(indent_char))
        item_name_part = line.strip()

        # Validate indentation
        if leading_chars_count % indent_unit != 0:
            if leading_chars_count == 0:
                 level = 0
            else:
                print(f"Warning (_parse_indent_based): Skipping line {line_num} due to inconsistent indentation (not multiple of {indent_unit}). Line: '{line}'")
                continue
        else:
            level = leading_chars_count // indent_unit

        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name:
            continue

        parsed_items.append((level, item_name, is_directory))

    if not parsed_items:
        print("Warning (_parse_indent_based): No parseable items found after processing all lines (check exclusions?).")
        return None # Return None, not empty list, consistent with other failures

    # Check if first *processed* item is level 0
    if parsed_items[0][0] != 0:
         print(f"Warning (_parse_indent_based): First parsed item is not level 0 (level is {parsed_items[0][0]}). Check map structure or exclusions.")

    return parsed_items

def _parse_tree_format(map_text, excluded_lines=None):
    """
    Parses tree-style formats (like tree command output, ASCII variants). (Cleaned)
    Skips lines specified in excluded_lines.
    """
    if excluded_lines is None: excluded_lines = set() # Ensure it's a set
    lines = map_text.strip().splitlines()
    if not lines: return None
    parsed_items = []
    indent_map = {}
    next_level_to_assign = 0
    last_level_processed = -1

    # MODIFIED: Use enumerate to get 1-based line numbers
    for line_num, line in enumerate(lines, start=1):
        # MODIFIED: Check if line should be excluded BEFORE processing
        if line_num in excluded_lines:
            continue

        original_line = line
        line = line.rstrip()
        if not line.strip(): continue # Skip blank lines

        item_name_part = line.lstrip(TREE_PREFIX_CHARS_TO_STRIP)
        indent_width = len(line) - len(line.lstrip())

        # ... (rest of level calculation logic remains the same) ...
        current_level = -1
        if indent_width not in indent_map:
             # ... (handle indent_width) ...
             if current_level == -1: # Check if level assignment failed
                  print(f"Warning (_parse_tree_format): Skipping line {line_num} due to potentially inconsistent/out-of-order indentation (width {indent_width}). Line: '{original_line}'")
                  continue
        else:
             current_level = indent_map[indent_width]

        if current_level > last_level_processed + 1 and line_num > 1: # Use line_num > 1 for jump check
             print(f"Warning (_parse_tree_format): Skipping line {line_num} due to unexpected jump > 1 in indentation level. Line: '{original_line}'")
             continue

        item_name_stripped = item_name_part.strip()
        is_directory = item_name_stripped.endswith('/')
        item_name = item_name_stripped.rstrip('/') if is_directory else item_name_stripped

        if not item_name:
            print(f"Warning (_parse_tree_format): Skipping line {line_num} as no item name found after stripping prefixes. Line: '{original_line}'")
            continue

        parsed_items.append((current_level, item_name, is_directory))
        last_level_processed = current_level

    if not parsed_items:
        print("Warning (_parse_tree_format): No parseable items found (check exclusions?).")
        return None # Return None

    return parsed_items

def _parse_generic_indent(map_text, excluded_lines=None):
    """
    Parses based on generic indentation width (fallback). Uses dynamic level mapping. (Cleaned)
    Skips lines specified in excluded_lines.
    """
    if excluded_lines is None: excluded_lines = set() # Ensure it's a set
    lines = map_text.strip().splitlines()
    if not lines: return None
    parsed_items = []
    indent_map = {}
    next_level_to_assign = 0
    last_level_processed = -1

    # MODIFIED: Use enumerate to get 1-based line numbers
    for line_num, line in enumerate(lines, start=1):
        # MODIFIED: Check if line should be excluded BEFORE processing
        if line_num in excluded_lines:
            continue

        original_line = line
        line = line.rstrip()
        if not line.strip(): continue # Skip blank lines

        leading_spaces = len(line) - len(line.lstrip(' '))
        item_name_part = PREFIX_STRIP_RE_GENERIC.sub("", line.lstrip(' ')).strip()
        indent_width = leading_spaces

        # ... (rest of level calculation logic remains the same) ...
        current_level = -1
        if indent_width not in indent_map:
             # ... (handle indent_width) ...
              if current_level == -1: # Check if level assignment failed
                   print(f"Warning (_parse_generic_indent): Skipping line {line_num} due to potentially inconsistent/out-of-order indentation. Line: '{original_line}'")
                   continue
        else:
            current_level = indent_map[indent_width]

        if current_level > last_level_processed + 1 and line_num > 1: # Use line_num > 1
             print(f"Warning (_parse_generic_indent): Skipping line {line_num} due to unexpected jump in indentation level. Line: '{original_line}'")
             continue

        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name:
             print(f"Warning (_parse_generic_indent): Skipping line {line_num} as no item name found after stripping prefixes. Line: '{original_line}'")
             continue

        parsed_items.append((current_level, item_name, is_directory))
        last_level_processed = current_level

    if not parsed_items:
        print("Warning (_parse_generic_indent): No parseable items found (check exclusions?).")
        return None # Return None

    if parsed_items and parsed_items[0][0] != 0:
        print("Warning (_parse_generic_indent): First parsed item does not seem to start at level 0.")

    return parsed_items
# --- Structure Creation Function ---
def create_structure_from_parsed(parsed_items, base_dir_str, queue=None):
    """
    Creates directory structure from parsed items list. (Cleaned Version)
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir(): return f"Error: Base directory '{base_dir_str}' is not valid.", False

    path_stack = [base_dir]
    created_root_name = "structure"
    total_items = len(parsed_items)

    try:
        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
            if queue:
                # Put progress update just before processing the item
                queue.put({'type': 'progress', 'current': i + 1, 'total': total_items})
            # Adjust stack depth
            target_stack_len = current_level + 1
            while len(path_stack) > target_stack_len:
                path_stack.pop()

            # Check consistency
            if len(path_stack) != target_stack_len:
                # Provide more context in error
                parent_level = len(path_stack) - 1
                raise ValueError(f"Structure Error for item '{item_name}' at level {current_level}. Cannot determine parent at level {parent_level}. Check map indentation consistency.")

            # Get parent and current path
            current_parent_path = path_stack[-1]
            # Basic sanitization for filename
            safe_item_name = re.sub(r'[<>:"/\\|?*]', '_', item_name)
            # Prevent completely empty names after sanitization
            if not safe_item_name:
                 safe_item_name = "_sanitized_empty_name_"
                 print(f"Warning: Item '{item_name}' resulted in empty name after sanitization, using '{safe_item_name}'.")

            current_path = current_parent_path / safe_item_name

            # Store root name
            if i == 0:
                 created_root_name = safe_item_name # Use sanitized name
                 if not is_directory: raise ValueError("Map must start with a directory.")

            # Create item
            if is_directory:
                current_path.mkdir(parents=True, exist_ok=True)
                path_stack.append(current_path)
            else: # Is file
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.touch(exist_ok=True)

    except ValueError as ve:
        # Return specific error from validation/stack logic
        return f"Error processing structure: {ve}", False
    except Exception as e:
        # Log unexpected errors if needed, but return user-friendly message
        print(f"ERROR in create_structure_from_parsed: Unhandled Exception: {e}")
        import traceback
        traceback.print_exc()
        failed_item = item_name if 'item_name' in locals() else 'unknown'
        return f"Error creating structure for item '{failed_item}': {e}", False

    # Success
    if queue:
         queue.put({'type': 'progress', 'current': total_items, 'total': total_items})
    return f"Structure for '{created_root_name}' successfully created in '{base_dir}'", True


# --- Example Usage / Test Harness ---
# (Keep the test harness as it was in the last version - it's useful for testing)
if __name__ == '__main__':
    # Ensure necessary imports for this block are present if run directly
    from pathlib import Path
    import shutil
    # import pprint # Keep commented out unless needed

    print("--- Testing Directory Mapper Logic (v7 - Cleaned Parsers) ---")

    # --- Setup Test Environment ---
    test_root = Path("./_mapper_test_env")
    if test_root.exists(): shutil.rmtree(test_root)
    test_root.mkdir()
    source_dir = test_root / "my_source_project_for_snapshot" # Use distinct name
    source_dir.mkdir()
    (source_dir / "README.md").touch()
    src_sub = source_dir / "src"
    src_sub.mkdir()
    (src_sub / "main.py").touch()
    data_sub = source_dir / "data"
    data_sub.mkdir()
    (data_sub / "info.txt").touch()
    print(f"\n1. Test Source Directory Structure Created in: {source_dir}")

    # --- Test Snapshot ---
    print("\n2. Testing Snapshot Function...")
    snapshot_output = create_directory_snapshot(str(source_dir))
    print("Snapshot Result (Spaces - 2):")
    print(snapshot_output)
    print("-" * 20)

    # --- Test Scaffold ---
    scaffold_base = test_root / "scaffold_output"
    scaffold_base.mkdir() # Base for all scaffold tests

    # Helper function for running scaffold tests
    def run_scaffold_test(test_num, hint, map_text, base_path_suffix):
        print(f"\n{test_num}. Testing Scaffold (hint='{hint}')...")
        test_dir = scaffold_base / base_path_suffix
        test_dir.mkdir(parents=True, exist_ok=True) # Ensure target base exists
        msg, success = create_structure_from_map(map_text, str(test_dir), format_hint=hint)
        print(f"Result: {success} - {msg}")
        # Basic verification: Check if the root item from map exists inside test_dir
        if success:
            try:
                first_line = map_text.strip().splitlines()[0].strip()
                root_name = first_line.rstrip('/')
                # Sanitize root name same way as creation logic
                safe_root_name = re.sub(r'[<>:"/\\|?*]', '_', root_name)
                if not safe_root_name: safe_root_name = "_sanitized_empty_name_"

                created_path = test_dir / safe_root_name
                if created_path.exists():
                     print(f"Verification: Item '{safe_root_name}' created successfully in {test_dir.name}.")
                else:
                     print(f"Verification WARNING: Success reported, but root item '{safe_root_name}' not found in {test_dir.name}.")
            except Exception as e:
                print(f"Verification ERROR: Could not verify result - {e}")
        return success

    # Test with explicit hint matching snapshot output
    run_scaffold_test(3, "Spaces (2)", snapshot_output, "s2_explicit")

    # Test with Auto-Detect (should detect Spaces (2))
    run_scaffold_test(4, "Auto-Detect", snapshot_output, "s2_auto")

    # --- Test other formats (using sample strings) ---
    map_spaces_4 = """
MyProject4/
    data/
        info.txt
    src/
        main.py
    README.md
"""
    run_scaffold_test(5, "Spaces (4)", map_spaces_4, "s4")

    map_tabs = """
MyProjectTabs/
\tdata/
\t\tinfo.txt
\tsrc/
\t\tmain.py
\tREADME.md
"""
    map_tabs = map_tabs.replace("    ", "\t") # Ensure tabs
    run_scaffold_test(6, "Tabs", map_tabs, "tabs")

    map_tree = """
MyProjectTree/
├── data/
│   └── info.txt
├── src/
│   └── main.py
└── README.md
"""
    run_scaffold_test(7, "Tree", map_tree, "tree")

    map_generic_mix = """
* MyProjectMix/
  - data/
    * info.txt/
  - src/
    * main.py
  - README.md
"""
    run_scaffold_test(8, "Generic", map_generic_mix, "generic")

    print("\n--- Testing Complete ---")
    print(f"\nTest environment left in: {test_root}")
    # Optional: Add cleanup
    # input("Press Enter to delete test environment...")
    # shutil.rmtree(test_root)
