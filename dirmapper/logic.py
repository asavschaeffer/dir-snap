# dirmapper/logic.py

import os
import fnmatch
import re # For format detection and parsing
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
# We will strip these from the left to find the start of the actual name.
TREE_PREFIX_CHARS_TO_STRIP = "│├└─| L\\_+-`" + " " + "\t"

# --- Snapshot Function (Unchanged from previous working version) ---

def create_directory_snapshot(root_dir_str, custom_ignore_patterns=None):
    """Generates map using DEFAULT_SNAPSHOT_SPACES and trailing '/'"""
    root_dir = Path(root_dir_str).resolve()
    if not root_dir.is_dir():
        return f"Error: Path is not a valid directory: {root_dir_str}"
    ignore_set = DEFAULT_IGNORE_PATTERNS.copy()
    if custom_ignore_patterns: ignore_set.update(custom_ignore_patterns)
    try:
        tree = {'name': root_dir.name, 'is_dir': True, 'children': [], 'path': root_dir}
        node_map = {root_dir: tree}
        for root, dirs, files in os.walk(str(root_dir), topdown=True, onerror=None):
            current_path = Path(root).resolve()
            parent_node = node_map.get(current_path)
            if parent_node is None:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore_set)]
            files = sorted([f for f in files if not any(fnmatch.fnmatch(f, pattern) for pattern in ignore_set)])
            dirs.sort()
            for d_name in dirs:
                dir_path = current_path / d_name
                child_node = {'name': d_name, 'is_dir': True, 'children': [], 'path': dir_path}
                parent_node['children'].append(child_node)
                node_map[dir_path] = child_node
            for f_name in files:
                 child_node = {'name': f_name, 'is_dir': False, 'path': current_path / f_name}
                 parent_node['children'].append(child_node)
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
        return f"Error during directory processing near {current_path if 'current_path' in locals() else root_dir}: {e}"


# ============================================================
# --- Scaffold Functions (Refactored for Multi-Format) ---
# ============================================================

# --- Main Public Function ---

def create_structure_from_map(map_text, base_dir_str, format_hint="Auto-Detect"):
    """
    Main scaffolding function. Parses map text based on format hint
    and creates the directory structure.
    """
    parsed_items = None
    error_msg = None
    print(f"Debug: Starting scaffold with format_hint='{format_hint}'") # Keep this high-level debug
    try:
        parsed_items = parse_map(map_text, format_hint)
        if parsed_items is None or not parsed_items:
             error_msg = "Failed to parse map text (empty map or format error?). Check console warnings."
    except Exception as parse_e:
        error_msg = f"Error during map parsing: {parse_e}"
        # import traceback # Keep commented out for future debugging if needed
        # traceback.print_exc()

    if error_msg:
         return error_msg, False

    # Call the structure creation function (which no longer prints verbosely)
    try:
        # REMOVED pprint call here
        return create_structure_from_parsed(parsed_items, base_dir_str)
    except Exception as create_e:
        return f"Fatal error during structure creation: {create_e}", False


# --- Parsing Orchestrator ---

def parse_map(map_text, format_hint):
    """
    Orchestrates parsing based on format hint or auto-detection.
    Returns parsed items list or None on failure.
    """
    actual_format = format_hint
    if format_hint == "Auto-Detect" or format_hint == "MVP Format":
        actual_format = _detect_format(map_text)
        print(f"Debug: Auto-detected format as: '{actual_format}'")

    if actual_format == "Spaces (2)":
        return _parse_indent_based(map_text, spaces_per_level=2)
    elif actual_format == "Spaces (4)":
        return _parse_indent_based(map_text, spaces_per_level=4)
    elif actual_format == "Tabs":
        return _parse_indent_based(map_text, use_tabs=True)
    elif actual_format == "Tree":
        return _parse_tree_format(map_text)
    elif actual_format == "Generic":
        print("Info: Using generic indentation parser as fallback.")
        return _parse_generic_indent(map_text)
    else: # Should not happen if hint comes from Combobox
        print(f"Warning: Unknown format hint '{actual_format}', attempting generic parse.")
        return _parse_generic_indent(map_text)

# --- Format Detection Helper ---
# Regex to detect tree prefixes more reliably after leading whitespace
TREE_PREFIX_RE = re.compile(r"^\s*([││]|├──|└──)") # Matches start, spaces, then a tree char

def _detect_format(map_text, sample_lines=20):
    """
    Analyzes the first few lines of map_text to detect the format.
    """
    lines = map_text.strip().splitlines()
    non_empty_lines = [line for line in lines if line.strip()][:sample_lines]
    if not non_empty_lines: return "Generic" # Treat empty as generic

    # 1. Check for Tree Prefixes
    if any(TREE_PREFIX_RE.match(line) for line in non_empty_lines[1:]): # Check from second line
        print("Debug: Detected tree characters.")
        return "Tree"

    # 2. Check for Tabs (on indented lines)
    indented_lines = [line for line in non_empty_lines if line and not line.isspace() and line[0] in ('\t', ' ')]
    if any(line.startswith('\t') for line in indented_lines):
        print("Debug: Detected leading tabs.")
        return "Tabs"

    # 3. Check for Spaces - analyze indent differences on non-blank, indented lines
    leading_spaces = [len(line) - len(line.lstrip(' ')) for line in indented_lines if line.startswith(' ')]
    space_indents = sorted(list(set(sp for sp in leading_spaces if sp > 0))) # Unique positive indents

    if not space_indents:
        # No indented lines found, or only root item present. Treat as simple case.
        # Could be space-based if there are spaces but no *increase* in indent.
        # Or generic if no spaces/tabs/tree at all.
        if any(line.startswith(' ') for line in non_empty_lines):
             # Default to most common space indent if some spaces exist but structure is flat/unclear
             print("Debug: Detected spaces but unclear indent level, assuming Spaces (2).")
             return "Spaces (2)"
        else:
             print("Debug: No clear indentation detected.")
             return "Generic" # No indentation found

    # Calculate differences between consecutive unique indent levels
    indent_diffs = {space_indents[i] - space_indents[i-1] for i in range(1, len(space_indents))}

    # Check for consistent increments (usually 2 or 4)
    if len(indent_diffs) == 1: # Only one increment value found
         diff = indent_diffs.pop()
         # Check if base indent is also a multiple of diff
         if space_indents[0] % diff == 0:
             if diff == 4:
                 print("Debug: Detected consistent space indentation (multiples of 4).")
                 return "Spaces (4)"
             elif diff == 2:
                 print("Debug: Detected consistent space indentation (multiples of 2).")
                 return "Spaces (2)"
             else: # Other consistent increment? Treat as generic for now.
                 print(f"Debug: Detected consistent space indentation (multiples of {diff}), using Generic.")
                 return "Generic"

    # If multiple differences or base indent doesn't match, assume generic/mixed
    print("Debug: Inconsistent space indentation increments detected.")
    return "Generic"

# --- Specific Parser Implementations ---
# Replace the existing _parse_indent_based function in dirmapper/logic.py
# with this version which includes debugging prints:

def _parse_indent_based(map_text, spaces_per_level=None, use_tabs=False):
    """
    Parses map text using consistent space or tab indentation.
    Relies on trailing '/' for directories. Returns parsed items list or None.
    Includes debugging prints for indentation checking.
    """
    if not (spaces_per_level or use_tabs):
        print("Error (_parse_indent_based): Specify spaces_per_level or use_tabs.")
        return None

    lines = map_text.strip().splitlines()
    if not lines:
        print("Warning (_parse_indent_based): Input map text is empty.")
        return None

    parsed_items = []
    indent_char = '\t' if use_tabs else ' '
    indent_unit = 1 if use_tabs else spaces_per_level
    if indent_unit <= 0:
        print("Error (_parse_indent_based): Indent unit must be positive.")
        return None

    print(f"DEBUG PARSER: Using IndentChar='{repr(indent_char)}', IndentUnit={indent_unit}") # Show config

    for line_num, line in enumerate(lines):
        print("-" * 10) # Separator for lines
        print(f"DEBUG PARSER: Processing Line {line_num+1}: '{line}'")

        if not line.strip():
            print("DEBUG PARSER: Skipping blank line.")
            continue # Skip blank lines

        # Calculate leading characters
        leading_chars_count = len(line) - len(line.lstrip(indent_char))
        print(f"DEBUG PARSER: Leading Chars Count ({repr(indent_char)}): {leading_chars_count}")

        item_name_part = line.strip() # Get name after all leading whitespace/tabs

        # Validate indentation
        if leading_chars_count % indent_unit != 0:
            print(f"DEBUG PARSER: Indent check FAILED: {leading_chars_count} % {indent_unit} != 0")
            # Allow level 0 (no indent)
            if leading_chars_count == 0 : # Removed 'and line_num == 0' check, level 0 is always valid indent=0
                 level = 0
                 print(f"DEBUG PARSER: Allowed level 0 (no indent).")
            else:
                print(f"Warning (_parse_indent_based): Skipping line {line_num+1} due to inconsistent indentation (not multiple of {indent_unit}). Line: '{line}'")
                continue # Skip this line completely
        else:
            level = leading_chars_count // indent_unit
            print(f"DEBUG PARSER: Indent OK. Calculated Level={level}")

        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name:
            print(f"DEBUG PARSER: Skipping line {line_num+1} because item name is empty after stripping.")
            continue # Skip if stripping leaves nothing

        print(f"DEBUG PARSER: Appending: (Level={level}, Name='{item_name}', IsDir={is_directory})")
        parsed_items.append((level, item_name, is_directory))

    # --- Post-loop checks ---
    if not parsed_items:
        print("Warning (_parse_indent_based): No parseable items found after processing all lines.")
        return None # Return None if nothing was parsed

    # Basic validation: First item should usually be level 0
    if parsed_items[0][0] != 0:
         print(f"Warning (_parse_indent_based): Parsed map does not seem to start at level 0 (first item level is {parsed_items[0][0]}).")
         # Allow this for now, structure creation handles level consistency.

    print("DEBUG PARSER: Parsing finished.")
    return parsed_items

def _parse_tree_format(map_text):
    """
    Parses tree-style formats (like tree command output, ASCII variants).
    Determines level based on effective indent after stripping prefixes.
    Relies on trailing '/' for directories. Returns parsed items list or None.
    """
    lines = map_text.strip().splitlines()
    if not lines: return None
    parsed_items = []

    # --- Dynamic Level Mapping ---
    indent_map = {} # Maps indent_width -> level
    next_level_to_assign = 0
    last_level_processed = -1

    for line_num, line in enumerate(lines):
        original_line = line # For logging/errors
        line = line.rstrip() # Strip trailing whitespace only
        if not line.strip(): continue # Skip blank lines

        # --- Find where the actual name starts ---
        # Strip all known prefix characters from the left
        item_name_part = line.lstrip(TREE_PREFIX_CHARS_TO_STRIP)
        # Calculate the effective indent width (column where name starts)
        indent_width = len(line) - len(line.lstrip()) # Overall indent works well here

        # --- Determine Level Dynamically ---
        current_level = -1 # Initialize level for this line
        if indent_width not in indent_map:
            # First time seeing this indent width
            if indent_width == 0 : # Root level must be 0
                current_level = 0
                indent_map[0] = 0
                if next_level_to_assign == 0: next_level_to_assign = 1
            # Check if it logically follows the previous level for assignment
            elif indent_width > max(indent_map.keys() if indent_map else [-1]): # Deeper than any known indent
                current_level = next_level_to_assign
                indent_map[indent_width] = current_level
                next_level_to_assign += 1
            else:
                # Found an existing indent width out of sequence? Indicates messy map.
                # Try to find closest existing level? Or skip? Let's skip for now.
                print(f"Warning (_parse_tree_format): Skipping line {line_num+1} due to potentially inconsistent/out-of-order indentation (width {indent_width}). Line: '{original_line}'")
                continue
        else:
            # Known indent width
            current_level = indent_map[indent_width]

        # --- Level Consistency Check ---
        # Allow same level, one level deeper, or any number of levels shallower
        if current_level > last_level_processed + 1 and line_num > 0:
             print(f"Warning (_parse_tree_format): Skipping line {line_num+1} due to unexpected jump > 1 in indentation level. Line: '{original_line}'")
             continue

        # --- Get Name and Type ---
        item_name_stripped = item_name_part.strip() # Should already be stripped, but be safe
        is_directory = item_name_stripped.endswith('/')
        item_name = item_name_stripped.rstrip('/') if is_directory else item_name_stripped

        if not item_name: # Skip if only prefixes remained
            print(f"Warning (_parse_tree_format): Skipping line {line_num+1} as no item name found after stripping prefixes. Line: '{original_line}'")
            continue

        # Append successfully parsed item
        parsed_items.append((current_level, item_name, is_directory))
        last_level_processed = current_level # Update for next line validation

    # --- Post-loop checks ---
    if not parsed_items:
        print("Warning (_parse_tree_format): No parseable items found.")
        return None

    # Don't warn about level 0 start, allow maps that are fragments
    # if parsed_items[0][0] != 0: print("Warning (_parse_tree_format): Map does not seem to start at level 0.")

    print("DEBUG PARSER: Tree parsing finished.")
    return parsed_items


def _parse_generic_indent(map_text):
    """
    Parses based on generic indentation width (fallback). Uses dynamic level mapping.
    Attempts to strip common list/tree prefixes. Relies on trailing '/' for directories.
    Returns parsed items list or None.
    """
    lines = map_text.strip().splitlines()
    if not lines: return None
    parsed_items = []

    # --- Dynamic Level Mapping ---
    indent_map = {} # Maps indent_width -> level
    next_level_to_assign = 0
    last_level_processed = -1

    # Regex to strip common list/tree prefixes AFTER leading spaces
    # Allows *, -, space, |, `, └, ├, T, t, > etc.
    # Make the stripping less aggressive than Tree parser perhaps? Focus on list markers.
    PREFIX_STRIP_RE_GENERIC = re.compile(r"^[ *\-\>`]+") # Common list/basic prefixes

    for line_num, line in enumerate(lines):
        original_line = line # For logging/errors
        line = line.rstrip()
        if not line.strip(): continue # Skip blank lines

        # --- Find where the actual name starts ---
        leading_spaces = len(line) - len(line.lstrip(' '))
        # Try stripping common list/basic prefixes AFTER the space indent
        item_name_part = PREFIX_STRIP_RE_GENERIC.sub("", line.lstrip(' ')).strip()
        # Use leading_spaces as the indent_width key
        indent_width = leading_spaces

        # --- Determine Level Dynamically (Same logic as tree parser) ---
        current_level = -1
        if indent_width not in indent_map:
            if indent_width == 0 : # Root level
                current_level = 0
                indent_map[0] = 0
                if next_level_to_assign == 0: next_level_to_assign = 1
            elif len(indent_map) == 0 and indent_width > 0: # First indented
                current_level = 1
                indent_map[indent_width] = 1
                indent_map[0] = 0 # Assume level 0 exists if not explicitly first
                next_level_to_assign = 2
            elif indent_width > max(indent_map.keys() if indent_map else [-1]): # Deeper
                current_level = next_level_to_assign
                indent_map[indent_width] = current_level
                next_level_to_assign += 1
            else: # Inconsistent indent width found
                print(f"Warning (_parse_generic_indent): Skipping line {line_num+1} due to potentially inconsistent/out-of-order indentation (width {indent_width}). Line: '{original_line}'")
                continue
        else: # Known indent width
            current_level = indent_map[indent_width]

        # --- Level Consistency Check ---
        if current_level > last_level_processed + 1 and line_num > 0:
             print(f"Warning (_parse_generic_indent): Skipping line {line_num+1} due to unexpected jump > 1 in indentation level. Line: '{original_line}'")
             continue

        # --- Get Name and Type ---
        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name: # Skip if only prefixes remained
            print(f"Warning (_parse_generic_indent): Skipping line {line_num+1} as no item name found after stripping prefixes. Line: '{original_line}'")
            continue

        parsed_items.append((current_level, item_name, is_directory))
        last_level_processed = current_level

    if not parsed_items:
        print("Warning (_parse_generic_indent): No parseable items found.")
        return None

    print("DEBUG PARSER: Generic parsing finished.")
    return parsed_items


# --- Structure Creation Function  ---
def create_structure_from_parsed(parsed_items, base_dir_str):
    """
    Creates directory structure from parsed items list.
    Includes debug print for root item's is_directory check.
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir(): return f"Error: Base directory '{base_dir_str}' is not valid.", False
    if not parsed_items: return "Error: No items parsed from map.", False

    path_stack = [base_dir]
    created_root_name = "structure"

    try:
        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
             # Root Item Handling
             if i == 0:
                 print(f"DEBUG CREATE: Checking Root Item '{item_name}'. Is Directory = {is_directory}") # <<<--- ADDED THIS LINE
                 created_root_name = item_name
                 if not is_directory: # Check the value passed in
                      raise ValueError("Map must start with a directory.")
             # Normal Item Handling
             else:
                 # Adjust stack depth
                 target_stack_len = current_level + 1
                 while len(path_stack) > target_stack_len:
                     path_stack.pop()

                 # Check consistency
                 if len(path_stack) != target_stack_len:
                     raise ValueError(f"STACK ERROR! Cannot determine parent directory for item '{item_name}' at level {current_level}. Expected stack len {target_stack_len}, got {len(path_stack)}.")

             # Get parent and current path (this needs to happen for root too, AFTER validation)
             current_parent_path = path_stack[-1]
             current_path = current_parent_path / item_name

             # Create item
             if is_directory:
                 current_path.mkdir(parents=True, exist_ok=True)
                 # Add this dir to stack
                 path_stack.append(current_path)
             else: # Is file
                 current_path.parent.mkdir(parents=True, exist_ok=True)
                 current_path.touch(exist_ok=True)

    except ValueError as ve:
        return f"Error processing structure: {ve}", False
    except Exception as e:
        print(f"ERROR in create_structure_from_parsed: Unhandled Exception: {e}")
        # import traceback
        # traceback.print_exc()
        return f"Error creating structure for item '{item_name}': {e}", False

    # Success
    return f"Structure for '{created_root_name}' successfully created in '{base_dir}'", True

# --- Example Usage / Test Harness ---
if __name__ == '__main__':
    # Ensure necessary imports for this block are present if run directly
    from pathlib import Path
    import shutil
    # Note: If run as 'python -m dirmapper.logic', functions are already defined.

    print("--- Testing Directory Mapper Logic (v7 - Harness Fix) ---")

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

    # Test with explicit hint matching snapshot output
    print("\n3. Testing Scaffold (hint='Spaces (2)')...")
    test_dir_s2_explicit = scaffold_base / "s2_explicit"
    test_dir_s2_explicit.mkdir(parents=True, exist_ok=True) # <<<--- ADDED THIS LINE
    msg_s2, success_s2 = create_structure_from_map(snapshot_output, str(test_dir_s2_explicit), format_hint="Spaces (2)")
    print(f"Result: {success_s2} - {msg_s2}")

    # Test with Auto-Detect (should detect Spaces (2))
    print("\n4. Testing Scaffold (hint='Auto-Detect' on Spaces map)...")
    test_dir_s2_auto = scaffold_base / "s2_auto"
    test_dir_s2_auto.mkdir(parents=True, exist_ok=True) # <<<--- Ensure this is present too
    msg_auto_s2, success_auto_s2 = create_structure_from_map(snapshot_output, str(test_dir_s2_auto), format_hint="Auto-Detect")
    print(f"Result: {success_auto_s2} - {msg_auto_s2}")

    # --- Test other formats (using sample strings) ---
    map_spaces_4 = """
MyProject4/
    data/
        info.txt
    src/
        main.py
    README.md
"""
    print("\n5. Testing Scaffold (hint='Spaces (4)')...")
    test_dir_s4 = scaffold_base / "s4"
    test_dir_s4.mkdir(parents=True, exist_ok=True) # <<<--- ADDED THIS LINE
    msg_s4, success_s4 = create_structure_from_map(map_spaces_4, str(test_dir_s4), format_hint="Spaces (4)")
    print(f"Result: {success_s4} - {msg_s4}")

    map_tabs = """
MyProjectTabs/
\tdata/
\t\tinfo.txt
\tsrc/
\t\tmain.py
\tREADME.md
"""
    map_tabs = map_tabs.replace("    ", "\t") # Ensure tabs
    print("\n6. Testing Scaffold (hint='Tabs')...")
    test_dir_tabs = scaffold_base / "tabs"
    test_dir_tabs.mkdir(parents=True, exist_ok=True) # <<<--- ADDED THIS LINE
    msg_tabs, success_tabs = create_structure_from_map(map_tabs, str(test_dir_tabs), format_hint="Tabs")
    print(f"Result: {success_tabs} - {msg_tabs}")

    map_tree = """
MyProjectTree/
├── data/
│   └── info.txt
├── src/
│   └── main.py
└── README.md
"""
    print("\n7. Testing Scaffold (hint='Tree')...")
    test_dir_tree = scaffold_base / "tree"
    test_dir_tree.mkdir(parents=True, exist_ok=True) # <<<--- ADDED THIS LINE
    msg_tree, success_tree = create_structure_from_map(map_tree, str(test_dir_tree), format_hint="Tree")
    print(f"Result: {success_tree} - {msg_tree}")

    map_generic_mix = """
* MyProjectMix/
  - data/
    * info.txt/
  - src/
    * main.py
  - README.md
"""
    print("\n8. Testing Scaffold (hint='Generic')...")
    test_dir_generic = scaffold_base / "generic"
    test_dir_generic.mkdir(parents=True, exist_ok=True) # <<<--- ADDED THIS LINE
    msg_gen, success_gen = create_structure_from_map(map_generic_mix, str(test_dir_generic), format_hint="Generic")
    print(f"Result: {success_gen} - {msg_gen}")

    print("\n--- Testing Complete ---")
    print(f"\nTest environment left in: {test_root}")
    # Optional: Add cleanup
    # input("Press Enter to delete test environment...")
    # shutil.rmtree(test_root)