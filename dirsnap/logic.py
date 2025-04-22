# filename: DirSnap/logic.py
# --- Combined and Corrected Version ---
# --- Tree Parser Fixed, Debug Prints Removed --- # Updated title

import os
import fnmatch
import re
from pathlib import Path
import shutil # Keep for test harness
from typing import NamedTuple, Optional, Set, List, Tuple, Dict, Any # Added NamedTuple, Optional etc.
# import copy # No longer needed after removing debug prints

# --- Default Configuration ---
DEFAULT_IGNORE_PATTERNS = {
    '.git', '.vscode', '__pycache__', 'node_modules', '.DS_Store',
    'build', 'dist', '*.pyc', '*.egg-info', '*.log', '.env',
    '*~', '*.tmp', '*.bak', '*.swp',
}
DEFAULT_SNAPSHOT_SPACES = 2 # Used for 'Standard Indent' format

# --- Tree Format Constants ---
TREE_BRANCH = "├── " # Includes space
TREE_LAST_BRANCH = "└── " # Includes space
TREE_PIPE = "│   "  # Pipe + spaces for alignment
TREE_SPACE = "    " # Space equivalent for levels below a last branch
TREE_LEVEL_UNIT_LEN = 4 # Length of TREE_PIPE or TREE_SPACE
# Characters that make up the tree structure prefixes (excluding item name)
TREE_STRUCTURE_CHARS = "│├└─ " # Pipe, branches, space

KNOWN_EMOJIS = ["📁", "📄"] # Define emojis clearly

# Regex to detect tree prefixes more reliably after leading whitespace (for detection)
TREE_PREFIX_RE = re.compile(r"^\s*([││]|├──|└──)")


# ============================================================
# --- Helper Functions and Data Structures ---
# ============================================================

# --- Helper for Final Emoji/Name Cleaning (Used by Tree Parser) ---
def _extract_final_components(text_remainder: str, original_line_for_warning: str = "") -> Tuple[str, str, bool]:
    """
    Extracts emoji, clean name, and directory status from the part of a line
    AFTER prefixes have been accounted for by the caller.

    Args:
        text_remainder: The part of the line starting with potential emoji or name.
        original_line_for_warning: The original line text for warning messages.

    Returns:
        Tuple: (detected_emoji, clean_name, is_directory)
    """
    detected_emoji = ""
    content_after_emoji = text_remainder

    # Detect and Measure Emoji
    emoji_len = 0
    space_after_emoji_len = 0
    for emoji in KNOWN_EMOJIS:
        # Use lstrip() to handle potential leading space before emoji
        if text_remainder.lstrip().startswith(emoji):
            detected_emoji = emoji
            emoji_len = len(emoji)
            emoji_start_index = text_remainder.find(emoji) # Find actual start
            temp_remainder = text_remainder[emoji_start_index + emoji_len:]
            if temp_remainder.startswith(' '):
                space_after_emoji_len = 1
            content_after_emoji = temp_remainder[space_after_emoji_len:]
            break

    # Final Name Extraction and Cleaning
    item_name_part = content_after_emoji
    is_directory = item_name_part.endswith('/')
    clean_name = item_name_part.rstrip('/').strip()

    if not clean_name and is_directory:
        # Log warning if needed, but don't print directly in library code
        # print(f"Warning: Line resulted in empty name but had directory marker: '{original_line_for_warning}'")
        pass

    return detected_emoji, clean_name, is_directory

# --- Older Helper (Used by Indent/Generic Parsers) ---
class LineComponents(NamedTuple):
    """Holds the dissected components of a map line (for Indent/Generic)."""
    raw_indent_width: int
    effective_indent_width: int # May not be accurate for Tree format if used here
    prefix_chars: str
    emoji: str
    clean_name: str
    is_directory: bool
    is_empty_or_comment: bool

def _extract_line_components(line_text: str) -> LineComponents:
    """
    Analyzes a single line of map text and extracts its components.
    (Used by Indent/Generic parsers ONLY)
    """
    original_line = line_text
    line_rstrip = line_text.rstrip()

    if not line_rstrip.strip() or line_rstrip.strip().startswith('#'):
        return LineComponents(
            raw_indent_width=len(line_text) - len(line_text.lstrip(' ')),
            effective_indent_width=0, prefix_chars="", emoji="", clean_name="",
            is_directory=False, is_empty_or_comment=True
        )

    raw_indent_width = len(line_rstrip) - len(line_rstrip.lstrip(' '))
    content_after_spaces = line_rstrip[raw_indent_width:]

    current_index = raw_indent_width
    detected_prefix = ""
    prefix_len = 0

    # Detect prefixes
    if content_after_spaces.startswith(TREE_BRANCH): prefix_len = len(TREE_BRANCH); detected_prefix = TREE_BRANCH
    elif content_after_spaces.startswith(TREE_LAST_BRANCH): prefix_len = len(TREE_LAST_BRANCH); detected_prefix = TREE_LAST_BRANCH
    elif content_after_spaces.startswith("- "): prefix_len = 2; detected_prefix = "- "
    elif content_after_spaces.startswith("* "): prefix_len = 2; detected_prefix = "* "

    current_index += prefix_len
    content_after_prefix = content_after_spaces[prefix_len:]

    # Detect emoji
    content_after_emoji = content_after_prefix
    detected_emoji = ""
    emoji_len = 0
    space_after_emoji_len = 0
    for emoji in KNOWN_EMOJIS:
        if content_after_prefix.startswith(emoji):
            detected_emoji = emoji; emoji_len = len(emoji)
            temp_remainder = content_after_prefix[emoji_len:]
            if temp_remainder.startswith(' '): space_after_emoji_len = 1
            content_after_emoji = temp_remainder[space_after_emoji_len:]
            break

    current_index += (emoji_len + space_after_emoji_len)
    effective_indent_width = current_index

    item_name_part = content_after_emoji
    is_directory = item_name_part.endswith('/')
    clean_name = item_name_part.rstrip('/').strip()

    if not clean_name and is_directory:
        # print(f"Warning: Line resulted in empty name but had directory marker: '{original_line.rstrip()}'")
        pass

    return LineComponents(
        raw_indent_width=raw_indent_width, effective_indent_width=effective_indent_width,
        prefix_chars=detected_prefix, emoji=detected_emoji, clean_name=clean_name,
        is_directory=is_directory, is_empty_or_comment=False
    )


# ============================================================
# --- Snapshot Function ---
# ============================================================
def create_directory_snapshot(root_dir_str, custom_ignore_patterns=None, user_default_ignores=None,
                               output_format="Standard Indent", show_emojis=False):
    """
    Generates an indented text map of a directory structure, supporting different formats.
    """
    root_dir = Path(root_dir_str).resolve()
    if not root_dir.is_dir():
        return f"Error: Path is not a valid directory: {root_dir_str}"

    # Combine ignore sets
    ignore_set = DEFAULT_IGNORE_PATTERNS.copy()
    if user_default_ignores:
        ignore_set.update(set(user_default_ignores))
    if custom_ignore_patterns:
        # Ensure custom patterns are treated as a set
        if isinstance(custom_ignore_patterns, str):
             custom_ignore_patterns = {p.strip() for p in custom_ignore_patterns.split(',') if p.strip()}
        elif isinstance(custom_ignore_patterns, (list, tuple)):
             custom_ignore_patterns = set(custom_ignore_patterns)

        if isinstance(custom_ignore_patterns, set):
             ignore_set.update(custom_ignore_patterns)
        elif custom_ignore_patterns is not None: # Handle unexpected types gracefully
             print(f"Warning: Invalid type for custom_ignore_patterns: {type(custom_ignore_patterns)}. Ignoring.")


    try:
        # Build Intermediate Tree using os.walk
        tree = {'name': root_dir.name, 'is_dir': True, 'children': [], 'path': root_dir}
        node_map = {root_dir: tree}
        current_path_for_error = root_dir

        for root, dirs, files in os.walk(str(root_dir), topdown=True, onerror=None, followlinks=False): # Added followlinks=False
            current_path = Path(root).resolve()
            current_path_for_error = current_path
            parent_node = node_map.get(current_path)

            if parent_node is None: # Should not happen if map is built correctly
                print(f"Warning: Parent node not found for path {current_path} during walk. Skipping.")
                dirs[:] = []; continue # Skip processing children of unmapped node

            # Pruning Directories
            dirs_to_keep = []
            for d in dirs:
                is_ignored = False
                dir_path_to_check = current_path / d # Check full path for ignores too potentially
                for pattern in ignore_set:
                    # Check name, name/, path, path/
                    if fnmatch.fnmatch(d, pattern) or \
                       fnmatch.fnmatch(str(dir_path_to_check), pattern) or \
                       (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(d, pattern.rstrip('/\\'))) or \
                       (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(str(dir_path_to_check), pattern.rstrip('/\\'))):
                        is_ignored = True; break
                if not is_ignored: dirs_to_keep.append(d)
            dirs[:] = dirs_to_keep # Modify dirs in place for os.walk pruning

            # Filter Files
            files_to_keep = []
            for f in files:
                 is_ignored = False
                 file_path_to_check = current_path / f
                 for pattern in ignore_set:
                      if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(str(file_path_to_check), pattern):
                           is_ignored = True; break
                 if not is_ignored: files_to_keep.append(f)
            files = sorted(files_to_keep) # Sort remaining files
            dirs.sort() # Sort remaining dirs

            # Add children to tree structure in memory
            for d_name in dirs:
                dir_path = current_path / d_name
                child_node = {'name': d_name, 'is_dir': True, 'children': [], 'path': dir_path}
                parent_node['children'].append(child_node)
                node_map[dir_path] = child_node # Add to map for descendant lookup
            for f_name in files:
                 file_path = current_path / f_name
                 child_node = {'name': f_name, 'is_dir': False, 'path': file_path}
                 parent_node['children'].append(child_node)
                 # Files don't need to be added to node_map as they have no children

        # --- Generate map string from the completed tree ---
        map_lines = []

        # Recursive helper function to build the output lines
        def build_map_lines_from_tree(node, level, prefix_str="", is_last=False):
            emoji_prefix = ""
            if show_emojis:
                emoji_prefix = KNOWN_EMOJIS[0] + " " if node['is_dir'] else KNOWN_EMOJIS[1] + " "

            indent_str = ""
            current_prefix = ""
            item_separator = "" # Usually empty

            if output_format == "Tabs":
                indent_str = "\t" * level
            elif output_format == "Tree":
                # Only add prefix elements if level > 0
                if level > 0:
                    indent_str = prefix_str # Prefix carries the │ and spaces
                    current_prefix = TREE_LAST_BRANCH if is_last else TREE_BRANCH
            else: # Default: "Standard Indent"
                indent_str = " " * (level * DEFAULT_SNAPSHOT_SPACES)

            suffix = "/" if node['is_dir'] else ""
            map_lines.append(f"{indent_str}{current_prefix}{item_separator}{emoji_prefix}{node['name']}{suffix}")

            # Recursively process children if it's a directory with children
            if node.get('children'):
                 child_prefix_addition = ""
                 if output_format == "Tree":
                      # If current node is last, its children get space prefix, otherwise pipe prefix
                      child_prefix_addition = TREE_SPACE if is_last else TREE_PIPE
                 next_prefix_str = prefix_str + child_prefix_addition if output_format == "Tree" else ""

                 sorted_children = sorted(node['children'], key=lambda x: (not x['is_dir'], x['name'].lower()))
                 num_children = len(sorted_children)
                 for i, child in enumerate(sorted_children):
                     child_is_last = (i == num_children - 1)
                     build_map_lines_from_tree(child, level + 1, next_prefix_str, child_is_last)

        # Iterate through the root's children to start the process
        root_children = sorted(tree.get('children', []), key=lambda x: (not x['is_dir'], x['name'].lower()))
        num_root_children = len(root_children)
        for i, child in enumerate(root_children):
             child_is_last = (i == num_root_children - 1)
             # Start first level items at level 0, with no prefix_str
             build_map_lines_from_tree(child, 0, "", child_is_last)

        return "\n".join(map_lines)

    except Exception as e:
        print(f"ERROR: Exception during directory snapshot near {current_path_for_error}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error during directory processing: {e}"

# ============================================================
# --- Scaffold Functions ---
# ============================================================
def create_structure_from_map(map_text: str, base_dir_str: str, format_hint: str = "Auto-Detect",
                              excluded_lines: Optional[Set[int]] = None,
                              queue: Optional[Any] = None) -> Tuple[str, bool, Optional[str]]:
    """
    Main scaffolding function. Parses map text based on format hint
    and creates the directory structure. Skips lines specified in excluded_lines.
    ALWAYS returns tuple: (message, success_bool, created_root_name or None)
    """
    parsed_items: Optional[List[Tuple[int, str, bool]]] = None
    error_msg: Optional[str] = None
    if excluded_lines is None: excluded_lines = set()

    # --- Parsing Step ---
    try:
        parsed_items = parse_map(map_text, format_hint, excluded_lines=excluded_lines)
        if parsed_items is None:
             error_msg = "Failed to parse map text (format error or no items found?). Check console warnings."
        elif not parsed_items:
             if map_text.strip(): error_msg = "Parsing resulted in no items (all lines might be excluded)."
             else: error_msg = "Map input is empty."
    except Exception as parse_e:
        error_msg = f"Error during map parsing: {parse_e}"
        print(f"ERROR: Exception during map parsing: {parse_e}")
        import traceback; traceback.print_exc()

    if error_msg: return error_msg, False, None
    if not parsed_items: return "Parsing resulted in no items.", False, None

    # --- Structure Creation Step ---
    try:
        return create_structure_from_parsed(parsed_items, base_dir_str, queue=queue)
    except Exception as create_e:
        print(f"ERROR: Unexpected exception calling create_structure_from_parsed: {create_e}")
        import traceback; traceback.print_exc()
        return f"Fatal error calling structure creation: {create_e}", False, None

def create_structure_from_parsed(parsed_items: List[Tuple[int, str, bool]], base_dir_str: str,
                                 queue: Optional[Any] = None) -> Tuple[str, bool, Optional[str]]:
    """
    Creates directory structure from parsed items list.
    Returns tuple: (message, success_bool, created_root_name_str or None)
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir():
        return f"Error: Base directory '{base_dir_str}' is not valid.", False, None

    path_stack: List[Path] = [base_dir]
    created_root_name: Optional[str] = None
    total_items = len(parsed_items)
    item_name_for_error = "<No Items Parsed>"

    try:
        if not parsed_items: return "Error: No parsed items to create.", False, None

        first_level, first_name, first_is_dir = parsed_items[0]
        if first_level != 0: raise ValueError(f"Map must start at level 0, but first item '{first_name}' is at level {first_level}.")
        if not first_is_dir: raise ValueError(f"Map must start with a directory, but first item '{first_name}' is not a directory.")
        item_name_for_error = first_name

        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
            item_name_for_error = item_name
            if queue: queue.put({'type': 'progress', 'current': i + 1, 'total': total_items})

            target_stack_len = current_level + 1
            while len(path_stack) > target_stack_len: path_stack.pop()

            if len(path_stack) != target_stack_len:
                parent_level = len(path_stack) - 1
                raise ValueError(
                    f"Structure Error for item '{item_name}' at level {current_level}. "
                    f"Inconsistent indentation detected. Expected parent at level {current_level - 1}, "
                    f"but current stack (len {len(path_stack)}) only goes up to level {parent_level}. "
                    f"Check map indentation near this item."
                )

            current_parent_path = path_stack[-1]
            safe_item_name = re.sub(r'[<>:"/\\|?*]', '_', item_name)
            safe_item_name = safe_item_name.strip('. ')
            if not safe_item_name:
                 safe_item_name = f"_sanitized_empty_name_{i}"
                 print(f"Warning: Item '{item_name}' resulted in empty name after sanitization, using '{safe_item_name}'.")

            current_path = current_parent_path / safe_item_name

            if i == 0: created_root_name = safe_item_name

            if is_directory:
                current_path.mkdir(parents=True, exist_ok=True)
                path_stack.append(current_path)
            else:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.touch(exist_ok=True)

    except ValueError as ve: return f"Error processing structure: {ve}", False, None
    except Exception as e:
        print(f"ERROR in create_structure_from_parsed loop: Unhandled Exception processing item '{item_name_for_error}': {e}")
        import traceback; traceback.print_exc()
        return f"Error creating structure near item '{item_name_for_error}': {e}", False, None

    if queue: queue.put({'type': 'progress', 'current': total_items, 'total': total_items})
    final_root_name = created_root_name if created_root_name else "_structure_empty_"
    return f"Structure for '{final_root_name}' successfully created in '{base_dir}'", True, final_root_name

# ============================================================
# --- Parsing Logic (Orchestrator, Detector, Parsers) ---
# ============================================================
def parse_map(map_text: str, format_hint: str, excluded_lines: Optional[Set[int]] = None) -> Optional[List[Tuple[int, str, bool]]]:
    """
    Orchestrates parsing based on format hint or auto-detection.
    """
    if excluded_lines is None: excluded_lines = set()

    actual_format = format_hint
    if format_hint == "Auto-Detect":
        actual_format = _detect_format(map_text)
        # print(f"Info: Auto-detected format as: '{actual_format}'") # Keep commented unless needed
        if actual_format == "Unknown":
             print("Warning: Could not reliably detect format. Attempting Generic parser.")
             actual_format = "Generic"

    parser_func = None
    if actual_format == "Spaces (2)": parser_func = lambda text, excludes: _parse_indent_based(text, excludes, spaces_per_level=2)
    elif actual_format == "Spaces (4)": parser_func = lambda text, excludes: _parse_indent_based(text, excludes, spaces_per_level=4)
    elif actual_format == "Tabs": parser_func = lambda text, excludes: _parse_indent_based(text, excludes, use_tabs=True)
    elif actual_format == "Tree": parser_func = _parse_tree_format # Uses NEW logic
    elif actual_format == "Generic": parser_func = _parse_generic_indent # Uses OLD helper
    else:
        print(f"Warning: Unknown format hint '{actual_format}', attempting generic parse.")
        parser_func = _parse_generic_indent # Uses OLD helper

    if parser_func: return parser_func(map_text, excluded_lines)
    else: print(f"Error: No parser function found for format '{actual_format}'."); return None

def _detect_format(map_text: str, sample_lines: int = 20) -> str:
    """
    Analyzes the first few lines of map_text to detect the format.
    """
    lines = map_text.strip().splitlines()
    non_empty_lines = [line for line in lines if line.strip()][:sample_lines]
    if not non_empty_lines: return "Generic"

    if any(line.lstrip().startswith((TREE_BRANCH, TREE_LAST_BRANCH)) for line in non_empty_lines): return "Tree"
    if any(TREE_PREFIX_RE.match(line) for line in non_empty_lines): return "Tree"
    if any(line.startswith('\t') for line in non_empty_lines if line and not line.isspace()): return "Tabs"

    indented_lines = [line for line in non_empty_lines if line and not line.isspace() and line[0] == ' ']
    leading_spaces = [len(line) - len(line.lstrip(' ')) for line in indented_lines]
    space_indents = sorted(list(set(sp for sp in leading_spaces if sp > 0)))

    if not space_indents: return "Generic"
    if all(s % 4 == 0 for s in space_indents): return "Spaces (4)"
    if all(s % 2 == 0 for s in space_indents): return "Spaces (2)"
    if len(space_indents) > 1: return "Generic"
    return "Generic"

# --- Specific Parser Implementations ---
def _parse_indent_based(map_text: str, excluded_lines: Set[int],
                        spaces_per_level: Optional[int] = None, use_tabs: bool = False) -> Optional[List[Tuple[int, str, bool]]]:
    """ Parses map text using consistent space or tab indentation. """
    if not (spaces_per_level or use_tabs): return None
    lines = map_text.splitlines()
    parsed_items: List[Tuple[int, str, bool]] = []
    indent_unit = 1 if use_tabs else spaces_per_level
    if indent_unit is None or indent_unit <= 0: return None

    for line_num, line in enumerate(lines, start=1):
        if line_num in excluded_lines: continue
        components = _extract_line_components(line) # Uses OLD helper
        if components.is_empty_or_comment: continue

        leading_chars_count = components.raw_indent_width if not use_tabs else len(line) - len(line.lstrip('\t'))
        level = -1

        if leading_chars_count % indent_unit != 0:
            if leading_chars_count == 0: level = 0
            else: print(f"Warning (_parse_indent_based): Skipping line {line_num} due to inconsistent indentation."); continue
        else: level = leading_chars_count // indent_unit

        item_name = components.clean_name
        is_directory = components.is_directory
        if not item_name: continue
        parsed_items.append((level, item_name, is_directory))

    if not parsed_items: return None
    if parsed_items and parsed_items[0][0] != 0: print(f"Warning (_parse_indent_based): First parsed item '{parsed_items[0][1]}' is at level {parsed_items[0][0]} (expected 0).")
    return parsed_items

def _parse_tree_format(map_text: str, excluded_lines: Set[int]) -> Optional[List[Tuple[int, str, bool]]]:
    """ (REVISED LOGIC) Parses tree-style formats by analyzing prefix structure. """
    lines = map_text.splitlines()
    parsed_items: List[Tuple[int, str, bool]] = []

    for line_num, line in enumerate(lines, start=1):
        original_line_rstrip = line.rstrip()
        if line_num in excluded_lines: continue
        if not original_line_rstrip.strip() or original_line_rstrip.strip().startswith('#'): continue

        current_level = 0
        name_remainder_index = 0
        while True:
            segment = original_line_rstrip[name_remainder_index : name_remainder_index + TREE_LEVEL_UNIT_LEN]
            if segment == TREE_PIPE or segment == TREE_SPACE:
                current_level += 1; name_remainder_index += TREE_LEVEL_UNIT_LEN
            else: break

        remainder_after_level = original_line_rstrip[name_remainder_index:]
        if remainder_after_level.startswith(TREE_BRANCH): name_remainder_index += len(TREE_BRANCH)
        elif remainder_after_level.startswith(TREE_LAST_BRANCH): name_remainder_index += len(TREE_LAST_BRANCH)

        name_remainder = original_line_rstrip[name_remainder_index:]
        _emoji, item_name, is_directory = _extract_final_components(name_remainder, original_line_rstrip)

        if not item_name: print(f"Warning (_parse_tree_format): Skipping line {line_num} as no item name found."); continue
        parsed_items.append((current_level, item_name, is_directory))

    if not parsed_items: return None
    return parsed_items

def _parse_generic_indent(map_text: str, excluded_lines: Set[int]) -> Optional[List[Tuple[int, str, bool]]]:
    """ Parses based on generic indentation width (fallback) using OLD helper. """
    lines = map_text.splitlines()
    if not lines: return None
    parsed_items: List[Tuple[int, str, bool]] = []
    indent_map: Dict[int, int] = {}
    last_level_processed = -1

    for line_num, line in enumerate(lines, start=1):
        if line_num in excluded_lines: continue
        components = _extract_line_components(line) # Uses OLD helper
        if components.is_empty_or_comment: continue

        indent_width = components.raw_indent_width
        current_level = -1

        if indent_width in indent_map: current_level = indent_map[indent_width]
        else:
            parent_level = -1; max_parent_indent = -1
            for known_indent, level in indent_map.items():
                if known_indent < indent_width:
                    if known_indent > max_parent_indent: max_parent_indent = known_indent; parent_level = level
            current_level = parent_level + 1
            indent_map[indent_width] = current_level
            keys_to_remove = {k for k, v in indent_map.items() if v > current_level}
            for k in keys_to_remove:
                 if k in indent_map: del indent_map[k]
            if indent_width not in indent_map: indent_map[indent_width] = current_level

        if current_level > last_level_processed + 1 and last_level_processed != -1: print(f"Warning (_parse_generic_indent): Skipping line {line_num} due to level jump."); continue

        item_name = components.clean_name
        is_directory = components.is_directory
        if not item_name: continue
        parsed_items.append((current_level, item_name, is_directory))
        last_level_processed = current_level

    if not parsed_items: return None
    if parsed_items and parsed_items[0][0] != 0: print(f"Warning (_parse_generic_indent): First item '{parsed_items[0][1]}' not level 0 (Level: {parsed_items[0][0]}).")
    return parsed_items


# --- Example Usage / Test Harness (Cleaned - No Prints) ---
if __name__ == '__main__':
    # Basic check to ensure module loads and functions exist
    print("--- Testing DirSnap Logic Module Load ---")
    test_root = Path("./_dirsnap_test_env_final")
    if test_root.exists(): shutil.rmtree(test_root)
    test_root.mkdir()
    source_dir = test_root / "src"
    source_dir.mkdir()
    (source_dir / "file.txt").touch()
    scaffold_base = test_root / "scaffold"
    scaffold_base.mkdir()

    # Test snapshot
    snap = create_directory_snapshot(str(source_dir), output_format="Tree")
    print(f"Snapshot Test Output:\n{snap}")

    # Test scaffold
    if snap:
        msg, success, root = create_structure_from_map(snap, str(scaffold_base), format_hint="Tree")
        print(f"\nScaffold Test Result: {success} - {msg}")
        if success and root and (scaffold_base / root).exists():
             print("Scaffold Verification: Root item exists.")
        elif success:
             print("Scaffold Verification WARNING: Success but root item missing or not returned.")
        else:
             print("Scaffold Verification: Failed as expected or unexpectedly.")

    # print(f"\nTest environment left in: {test_root}")
    # Consider cleanup
    try:
        shutil.rmtree(test_root)
        print(f"\nCleaned up test environment: {test_root}")
    except Exception as e:
        print(f"\nError cleaning up test environment: {e}")

