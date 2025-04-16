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
    Parses tree-style formats (like tree command output). Basic Implementation.
    Relies on prefix structure for level and trailing '/' for directories.
    """
    lines = map_text.strip().splitlines()
    if not lines: return None
    parsed_items = []
    # Regex to capture prefix and name:
    # Group 1: Full prefix (e.g., "│   ├── ")
    # Group 2: Item name (e.g., "file.txt" or "folder/")
    # Handles prefixes like │ ├── └── etc. followed by space
    TREE_LINE_RE = re.compile(r"^([││ \t]*[└├]?[─]?[─]?\s)?(.*)")

    for line_num, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip: continue

        match = TREE_LINE_RE.match(line)
        if match:
            prefix = match.group(1) or ""
            item_name_part = match.group(2).strip()

            # Calculate level based on prefix length / structure (crude estimate)
            # Each '│   ' or '    ' segment before the final marker adds a level.
            # A more robust way counts segments of length 4?
            visual_indent = len(prefix)
            level = visual_indent // 4 # Rough guess for typical tree output

            # Refine level for root (often has no prefix)
            if line_num == 0 and not prefix.strip():
                 level = 0

            is_directory = item_name_part.endswith('/')
            item_name = item_name_part.rstrip('/') if is_directory else item_name_part

            if not item_name: continue

            parsed_items.append((level, item_name, is_directory))
        else:
             # Should not happen with the broad regex, but indicates weird line
             print(f"Warning (_parse_tree_format): Could not parse line {line_num+1}: '{line}'")
             continue # Skip unparseable lines

    if not parsed_items: return None
    if parsed_items[0][0] != 0: print("Warning (_parse_tree_format): Map does not seem to start at level 0.")
    return parsed_items


def _parse_generic_indent(map_text):
    """
    Parses based on generic indentation width (fallback). Uses dynamic level mapping.
    Relies on trailing '/' for directories. Returns parsed items list or None.
    """
    lines = map_text.strip().splitlines()
    if not lines: return None

    parsed_items = []
    # Regex to strip common prefixes after leading whitespace
    # Allows *, -, space, |, `, └, ├, T, t prefixes
    PREFIX_STRIP_RE = re.compile(r"^[ *\-\|`└├Tt]+")

    indent_map = {} # Maps indent_width -> level
    next_level = 0
    last_level = -1 # For validation

    for line_num, line in enumerate(lines):
        line_strip_space = line.lstrip(' ') # Check space indent first
        if not line_strip_space.strip(): continue # Skip blank lines

        leading_spaces = len(line) - len(line_strip_space)
        # Try stripping common list/tree prefixes AFTER the space indent
        item_name_part = PREFIX_STRIP_RE.sub("", line_strip_space).strip()

        # Use leading_spaces as the indent_width key
        indent_width = leading_spaces

        # Determine Level based on indent_width mapping
        if indent_width not in indent_map:
            # Assign the next available level to this new indent width
            # Basic check: new indent should correspond to next level unless it's 0
            expected_level = last_level + 1
            if indent_width == 0: # Root level
                 current_level = 0
                 indent_map[0] = 0
                 if next_level == 0: next_level = 1 # Prepare for level 1
            elif len(indent_map) == 0 and indent_width > 0: # First indented item
                 current_level = 1
                 indent_map[indent_width] = 1
                 indent_map[0] = 0 # Assume level 0 exists
                 next_level = 2
            elif indent_width > max(indent_map.keys() if indent_map else [-1]): # Definitely deeper
                 current_level = next_level
                 indent_map[indent_width] = current_level
                 next_level += 1
            else:
                 # Indent width seen before, but maybe out of order? Or inconsistent?
                 # This indicates a potentially broken map structure for generic parsing
                 print(f"Warning (_parse_generic_indent): Skipping line {line_num+1} due to potentially inconsistent/out-of-order indentation. Line: '{line}'")
                 continue
        else:
            current_level = indent_map[indent_width]

        # Basic validation against previous level
        # Allow going shallower, staying same, or one level deeper
        if current_level > last_level + 1 and line_num > 0:
             print(f"Warning (_parse_generic_indent): Skipping line {line_num+1} due to unexpected jump in indentation level. Line: '{line}'")
             continue

        is_directory = item_name_part.endswith('/')
        item_name = item_name_part.rstrip('/') if is_directory else item_name_part

        if not item_name: continue

        parsed_items.append((current_level, item_name, is_directory))
        last_level = current_level # Update for next line validation

    if not parsed_items: return None
    if parsed_items[0][0] != 0: print("Warning (_parse_generic_indent): Map does not seem to start at level 0.")
    return parsed_items


# --- Structure Creation Function  ---
def create_structure_from_parsed(parsed_items, base_dir_str):
    """
    Creates directory structure from parsed items list. (Cleaned Version)
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir(): return f"Error: Base directory '{base_dir_str}' is not valid.", False
    if not parsed_items: return "Error: No items parsed from map.", False

    path_stack = [base_dir]
    created_root_name = "structure"

    try:
        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
            # Adjust stack depth
            target_stack_len = current_level + 1
            while len(path_stack) > target_stack_len:
                path_stack.pop()

            # Check consistency
            if len(path_stack) != target_stack_len:
                raise ValueError(f"STACK ERROR! Cannot determine parent directory for item '{item_name}' at level {current_level}. Expected stack len {target_stack_len}, got {len(path_stack)}.")

            # Get parent and current path
            current_parent_path = path_stack[-1]
            current_path = current_parent_path / item_name

            # Store root name
            if i == 0:
                 created_root_name = item_name
                 if not is_directory: raise ValueError("Map must start with a directory.")

            # Create item
            if is_directory:
                current_path.mkdir(parents=True, exist_ok=True)
                # Add this dir to stack ONLY if we went deeper or it's the root
                # (Need to check against previous level conceptually, but the stack adjustment logic handles this)
                # Simplest is to always push directory onto stack after creation
                path_stack.append(current_path)
            else: # Is file
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.touch(exist_ok=True)

    except ValueError as ve:
        # Errors still caught and returned, just not printed here
        return f"Error processing structure: {ve}", False
    except Exception as e:
        # Log unexpected errors if needed, but return user-friendly message
        print(f"ERROR in create_structure_from_parsed: Unhandled Exception: {e}") # Optional console log
        # import traceback # Keep commented out
        # traceback.print_exc()
        return f"Error creating structure for item '{item_name}': {e}", False

    # Success
    return f"Structure for '{created_root_name}' successfully created in '{base_dir}'", True
    print("--- Testing Directory Mapper Logic (v5 - Multi-Format Scaffold Parsers) ---")

    # --- Setup Test Environment ---
    test_root = Path("./_mapper_test_env")
    if test_root.exists(): shutil.rmtree(test_root)
    test_root.mkdir()
    source_dir = test_root / "my_source_project"
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
    scaffold_base.mkdir()

    # Test with explicit hint matching snapshot output
    print("\n3. Testing Scaffold (hint='Spaces (2)')...")
    msg, success = create_structure_from_map(snapshot_output, str(scaffold_base), format_hint="Spaces (2)")
    print(f"Result: {success} - {msg}")
    # TODO: Add verification logic for created structure

    # Test with Auto-Detect (should detect Spaces (2))
    print("\n4. Testing Scaffold (hint='Auto-Detect')...")
    msg_auto, success_auto = create_structure_from_map(snapshot_output, str(scaffold_base / "auto"), format_hint="Auto-Detect")
    print(f"Result: {success_auto} - {msg_auto}")

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
    msg_s4, success_s4 = create_structure_from_map(map_spaces_4, str(scaffold_base / "s4"), format_hint="Spaces (4)")
    print(f"Result: {success_s4} - {msg_s4}")

    map_tabs = """
MyProjectTabs/
\tdata/
\t\tinfo.txt
\tsrc/
\t\tmain.py
\tREADME.md
"""
    # Note: Need to be careful with literal tabs vs spaces in editor/string
    map_tabs = map_tabs.replace("    ", "\t") # Ensure tabs if copy-pasted
    print("\n6. Testing Scaffold (hint='Tabs')...")
    msg_tabs, success_tabs = create_structure_from_map(map_tabs, str(scaffold_base / "tabs"), format_hint="Tabs")
    print(f"Result: {success_tabs} - {msg_tabs}")

    map_tree = """
MyProjectTree/
├── data/
│   └── info.txt
├── src/
│   └── main.py
└── README.md
"""
    print("\n7. Testing Scaffold (hint='Tree' - Not Implemented)...")
    msg_tree, success_tree = create_structure_from_map(map_tree, str(scaffold_base / "tree"), format_hint="Tree")
    print(f"Result: {success_tree} - {msg_tree}") # Expect failure message

    map_generic = """
* MyProjectGeneric/
 * data/
  * info.txt
 * src/
  * main.py
 * README.md
"""
    print("\n8. Testing Scaffold (hint='Generic' - Not Implemented)...")
    msg_gen, success_gen = create_structure_from_map(map_generic, str(scaffold_base / "generic"), format_hint="Generic")
    print(f"Result: {success_gen} - {msg_gen}") # Expect fallback/failure message

    print("\n--- Testing Complete ---")
    print(f"\nTest environment left in: {test_root}")