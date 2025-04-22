# filename: DirSnap/logic.py
# --- Combined and Corrected Version ---
# --- Tree Parser Fixed, Emojis Expanded, Test Harness Enhanced --- # Updated title

import os
import fnmatch
import re
from pathlib import Path
from typing import NamedTuple, Optional, Set, List, Tuple, Dict, Any # Added NamedTuple, Optional etc.

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

# --- Expanded Emojis ---
FOLDER_EMOJI = "📁"
DEFAULT_FILE_EMOJI = "📄" # Fallback for unknown types

# Dictionary mapping lowercase extensions to emojis
FILE_TYPE_EMOJIS = {
    # Code & Scripts
    "py": "🐍", "js": "📜", "html": "🌐", "css": "🎨", "java": "☕", "c": "🇨",
    "cpp": "🇨", "cs": "♯", "go": "🐹", "rb": "💎", "php": "🐘", "swift": "🐦",
    "kt": "💜", "rs": "🦀", "sh": "💲", "bat": "🦇", "ps1": " PowerShell",
    "json": "⚙️", "xml": "📰", "yaml": "🧾", "yml": "🧾", "toml": "⚙️",
    "md": "📝", "rst": "📝", "tex": "🎓",
    # Text & Documents
    "txt": "📄", "rtf": "📄", "log": "🪵", "csv": "📊",
    "doc": "💼", "docx": "💼", "odt": "💼", "pdf": "📕", "ppt": "📽️",
    "pptx": "📽️", "xls": "📈", "xlsx": "📈",
    # Images
    "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "gif": "🖼️", "bmp": "🖼️",
    "tif": "🖼️", "tiff": "🖼️", "svg": "🎨", "ico": "🖼️", "webp": "🖼️",
    # Audio
    "mp3": "🎵", "wav": "🎵", "ogg": "🎵", "flac": "🎵", "aac": "🎵", "m4a": "🎵",
    # Video
    "mp4": "🎬", "mov": "🎬", "avi": "🎬", "mkv": "🎬", "wmv": "🎬", "flv": "🎬",
    "webm": "🎬",
    # Archives
    "zip": "📦", "rar": "📦", "7z": "📦", "tar": "📦", "gz": "📦", "bz2": "📦",
    # Data & DB
    "db": "💾", "sql": "💾", "sqlite": "💾", "sqlite3": "💾",
    # System & Config
    "ini": "⚙️", "cfg": "⚙️", "conf": "⚙️", "env": "🔒", "lock": "🔒",
    # Others
    "exe": "🚀", "app": "🚀", "dmg": "📀", "iso": "📀", "bin": "⚙️",
    "gitignore": "🚫", "dockerfile": "🐳",
}
# --- End Expanded Emojis ---

# Regex to detect tree prefixes more reliably after leading whitespace (for detection)
TREE_PREFIX_RE = re.compile(r"^\s*([││]|├──|└──)")


# ============================================================
# --- Helper Functions and Data Structures ---
# ============================================================

# --- Helper for Final Emoji/Name Cleaning (Used by Tree Parser) ---
def _extract_final_components(text_remainder: str, original_line_for_warning: str = "") -> Tuple[str, str, bool]:
    """
    Extracts emoji, clean name, and directory status from the part of a line
    AFTER prefixes have been accounted for by the caller. Handles new emojis.

    Args:
        text_remainder: The part of the line starting with potential emoji or name.
        original_line_for_warning: The original line text for warning messages.

    Returns:
        Tuple: (detected_emoji, clean_name, is_directory)
    """
    # Dynamically build list of known emojis for parsing this line
    parse_known_emojis = list(set([FOLDER_EMOJI, DEFAULT_FILE_EMOJI] + list(FILE_TYPE_EMOJIS.values())))

    detected_emoji = ""
    content_after_emoji = text_remainder

    # Detect and Measure Emoji
    emoji_len = 0
    space_after_emoji_len = 0
    # Check for potential leading space before emoji
    stripped_remainder = text_remainder.lstrip()
    for emoji in parse_known_emojis:
        if stripped_remainder.startswith(emoji):
            detected_emoji = emoji
            emoji_len = len(emoji)
            # Find where the emoji actually starts in the original remainder
            emoji_start_index = text_remainder.find(emoji)
            temp_remainder = text_remainder[emoji_start_index + emoji_len:]
            # Check for exactly one space after the emoji
            if temp_remainder.startswith(' '):
                space_after_emoji_len = 1
            content_after_emoji = temp_remainder[space_after_emoji_len:]
            break # Found the first matching emoji

    # Final Name Extraction and Cleaning
    item_name_part = content_after_emoji
    is_directory = item_name_part.endswith('/')
    clean_name = item_name_part.rstrip('/').strip()

    # Handle potential edge case: directory marker but empty name
    if not clean_name and is_directory:
        # print(f"Warning: Line resulted in empty name but had directory marker: '{original_line_for_warning}'")
        pass # Avoid printing in library code

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
    (Used by Indent/Generic parsers ONLY, updated for new emojis)
    """
    original_line = line_text
    line_rstrip = line_text.rstrip()

    # Handle empty lines or comments
    if not line_rstrip.strip() or line_rstrip.strip().startswith('#'):
        return LineComponents(
            raw_indent_width=len(line_text) - len(line_text.lstrip(' ')), # Preserve original indent if needed
            effective_indent_width=0, prefix_chars="", emoji="", clean_name="",
            is_directory=False, is_empty_or_comment=True
        )

    raw_indent_width = len(line_rstrip) - len(line_rstrip.lstrip(' '))
    content_after_spaces = line_rstrip[raw_indent_width:]

    current_index = raw_indent_width
    detected_prefix = ""
    prefix_len = 0

    # Detect structure prefixes first
    if content_after_spaces.startswith(TREE_BRANCH):
        prefix_len = len(TREE_BRANCH); detected_prefix = TREE_BRANCH
    elif content_after_spaces.startswith(TREE_LAST_BRANCH):
        prefix_len = len(TREE_LAST_BRANCH); detected_prefix = TREE_LAST_BRANCH
    elif content_after_spaces.startswith("- "):
        prefix_len = 2; detected_prefix = "- "
    elif content_after_spaces.startswith("* "):
        prefix_len = 2; detected_prefix = "* "
    # Add more prefixes here if needed

    current_index += prefix_len
    content_after_prefix = content_after_spaces[prefix_len:]

    # Dynamically build list of known emojis for parsing this line
    parse_known_emojis = list(set([FOLDER_EMOJI, DEFAULT_FILE_EMOJI] + list(FILE_TYPE_EMOJIS.values())))

    # Detect emoji *after* prefix
    content_after_emoji = content_after_prefix
    detected_emoji = ""
    emoji_len = 0
    space_after_emoji_len = 0
    stripped_after_prefix = content_after_prefix.lstrip() # Check for emoji after potential space
    for emoji in parse_known_emojis:
        if stripped_after_prefix.startswith(emoji):
            detected_emoji = emoji; emoji_len = len(emoji)
            emoji_start_index = content_after_prefix.find(emoji) # Find actual start
            temp_remainder = content_after_prefix[emoji_start_index + emoji_len:]
            if temp_remainder.startswith(' '): space_after_emoji_len = 1
            content_after_emoji = temp_remainder[space_after_emoji_len:]
            break

    # Update index based on actual emoji position and space
    if detected_emoji:
        current_index = raw_indent_width + content_after_prefix.find(detected_emoji) + emoji_len + space_after_emoji_len
    else:
        # If no emoji, effective indent is just after prefix (and any leading spaces)
        current_index = raw_indent_width + prefix_len + (len(content_after_prefix) - len(content_after_prefix.lstrip()))

    effective_indent_width = current_index # This might still be complex for generic use

    item_name_part = content_after_emoji
    is_directory = item_name_part.endswith('/')
    clean_name = item_name_part.rstrip('/').strip()

    if not clean_name and is_directory:
        # print(f"Warning: Line resulted in empty name but had directory marker: '{original_line.rstrip()}'")
        pass

    return LineComponents(
        raw_indent_width=raw_indent_width,
        effective_indent_width=effective_indent_width, # Use with caution
        prefix_chars=detected_prefix,
        emoji=detected_emoji,
        clean_name=clean_name,
        is_directory=is_directory,
        is_empty_or_comment=False
    )


# filename: dirsnap/logic.py

# ============================================================
# --- Snapshot Function ---
# ============================================================
def create_directory_snapshot(root_dir_str, custom_ignore_patterns=None, user_default_ignores=None,
                               output_format="Standard Indent", show_emojis=False):
    """
    Generates an indented text map of a directory structure, supporting different formats
    and expanded emojis. Includes the root directory name in the map.
    """
    root_dir = Path(root_dir_str).resolve()
    if not root_dir.is_dir():
        return f"Error: Path is not a valid directory: {root_dir_str}"

    # --- Ignore Pattern Handling ---
    ignore_set = DEFAULT_IGNORE_PATTERNS.copy()
    if user_default_ignores:
        if isinstance(user_default_ignores, set):
            ignore_set.update(user_default_ignores)
        elif isinstance(user_default_ignores, (list, tuple)):
             ignore_set.update(set(user_default_ignores))
        else:
             print(f"Warning: Invalid type for user_default_ignores: {type(user_default_ignores)}. Ignoring.")

    if custom_ignore_patterns:
        # Ensure custom patterns are treated as a set
        if isinstance(custom_ignore_patterns, str):
             custom_patterns_set = {p.strip() for p in custom_ignore_patterns.split(',') if p.strip()}
        elif isinstance(custom_ignore_patterns, (list, tuple)):
             custom_patterns_set = set(custom_ignore_patterns)
        elif isinstance(custom_ignore_patterns, set):
             custom_patterns_set = custom_ignore_patterns
        else:
             print(f"Warning: Invalid type for custom_ignore_patterns: {type(custom_ignore_patterns)}. Ignoring.")
             custom_patterns_set = set() # Ensure it's a set

        if custom_patterns_set:
            ignore_set.update(custom_patterns_set)
    # --- End Ignore Pattern Handling ---

    try:
        # --- Build Intermediate Tree using os.walk ---
        # Stores {'name': str, 'is_dir': bool, 'children': list, 'path': Path}
        tree = {'name': root_dir.name, 'is_dir': True, 'children': [], 'path': root_dir}
        node_map = {root_dir: tree} # Map Path objects to their nodes in the tree
        current_path_for_error = root_dir # For error reporting

        for root, dirs, files in os.walk(str(root_dir), topdown=True, onerror=None, followlinks=False):
            current_path = Path(root).resolve()
            current_path_for_error = current_path
            parent_node = node_map.get(current_path)

            if parent_node is None: # Safety check
                print(f"Warning: Parent node not found for path {current_path} during walk. Skipping children.")
                dirs[:] = []; files[:] = []; continue

            # --- Pruning Directories (Modify dirs in-place) ---
            dirs_to_keep = []
            for d in dirs:
                is_ignored = False
                dir_path_to_check = current_path / d
                for pattern in ignore_set:
                    if (fnmatch.fnmatch(d, pattern) or
                        fnmatch.fnmatch(str(dir_path_to_check), pattern) or
                        (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(d, pattern.rstrip('/\\'))) or
                        (pattern.endswith(('/', '\\')) and fnmatch.fnmatch(str(dir_path_to_check), pattern.rstrip('/\\')))):
                        is_ignored = True
                        break
                if not is_ignored:
                    dirs_to_keep.append(d)
            dirs[:] = sorted(dirs_to_keep) # Modify dirs *in place* and sort

            # --- Filtering Files ---
            files_to_keep = []
            for f in files:
                 is_ignored = False
                 file_path_to_check = current_path / f
                 for pattern in ignore_set:
                      if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(str(file_path_to_check), pattern):
                           is_ignored = True
                           break
                 if not is_ignored:
                     files_to_keep.append(f)
            files = sorted(files_to_keep) # Sort remaining files

            # --- Add children nodes to the tree structure in memory ---
            for d_name in dirs: # Already sorted
                dir_path = current_path / d_name
                child_node = {'name': d_name, 'is_dir': True, 'children': [], 'path': dir_path}
                parent_node['children'].append(child_node)
                node_map[dir_path] = child_node

            for f_name in files: # Already sorted
                 file_path = current_path / f_name
                 child_node = {'name': f_name, 'is_dir': False, 'path': file_path}
                 parent_node['children'].append(child_node)

        # --- Generate map string from the completed tree ---
        map_lines = []

        # Recursive helper function to build the output lines
        def build_map_lines_from_tree(node, level, prefix_str="", is_last=False):
            # --- EMOJI LOGIC USING EXPANDED DEFINITIONS ---
            emoji_prefix = ""
            if show_emojis:
                if node['is_dir']:
                    emoji_prefix = FOLDER_EMOJI + " "
                else:
                    file_name = node.get('name', '')
                    parts = file_name.split('.')
                    extension = parts[-1].lower() if len(parts) > 1 and parts[-1] else ''
                    if file_name.lower().endswith(".tar.gz"): extension = "gz"
                    elif file_name.lower().endswith(".tar.bz2"): extension = "bz2"
                    file_emoji = FILE_TYPE_EMOJIS.get(extension, DEFAULT_FILE_EMOJI)
                    emoji_prefix = file_emoji + " "
            # --- END OF EMOJI LOGIC ---

            indent_str = ""
            current_prefix = ""
            item_separator = ""

            # Determine indentation and prefix based on format
            if output_format == "Tabs":
                indent_str = "\t" * level
            elif output_format == "Tree":
                if level > 0: # Apply tree structure only from level 1 onwards
                    indent_str = prefix_str
                    current_prefix = TREE_LAST_BRANCH if is_last else TREE_BRANCH
                # Level 0 (root) gets no indent_str or current_prefix from tree logic
            else: # Default: "Standard Indent"
                indent_str = " " * (level * DEFAULT_SNAPSHOT_SPACES)

            suffix = "/" if node['is_dir'] else ""
            # Special case: Root node (level 0) name doesn't get the suffix automatically
            # from os.walk, so add it if it's a directory.
            if level == 0 and node['is_dir'] and not node['name'].endswith('/'):
                name_to_display = node['name'] + '/'
            else:
                # For children or files, name is usually correct from os.walk or intermediate build
                name_to_display = node['name'] + suffix


            map_lines.append(f"{indent_str}{current_prefix}{item_separator}{emoji_prefix}{name_to_display.strip('/')}{suffix}") # Ensure suffix is added correctly


            # Recursively process children if it's a directory with children
            if node.get('children'):
                 child_prefix_addition = ""
                 # Determine prefix addition needed for Tree format children
                 if output_format == "Tree":
                      child_prefix_addition = TREE_SPACE if is_last else TREE_PIPE
                 next_prefix_str = prefix_str + child_prefix_addition

                 sorted_children = sorted(node['children'], key=lambda x: (not x['is_dir'], x['name'].lower()))
                 num_children = len(sorted_children)
                 for i, child in enumerate(sorted_children):
                     child_is_last = (i == num_children - 1)
                     # Recursive call for each child, increasing level
                     build_map_lines_from_tree(child, level + 1, next_prefix_str, child_is_last)

        # --- Start the recursive generation process ---
        # Initiate the process by calling the helper function with the root node (tree) itself.
        # The root node will be rendered at level 0. Its children will be level 1+.
        build_map_lines_from_tree(tree, level=0, prefix_str="", is_last=True)

        return "\n".join(map_lines)

    except Exception as e:
        print(f"ERROR: Unhandled exception during directory snapshot near {current_path_for_error}: {e}")
        traceback.print_exc() # Print full traceback for debugging
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
             # Check if the original map wasn't just whitespace or comments
             if map_text.strip() and not all(l.strip().startswith('#') or not l.strip() for l in map_text.splitlines()):
                 error_msg = "Failed to parse map text (format error or unknown?). Check console warnings."
             else:
                 error_msg = "Map input is empty or contains only comments." # More specific
        elif not parsed_items:
             # Check if map had content but all was excluded
             if map_text.strip() and excluded_lines and len(excluded_lines) >= len([l for l in map_text.splitlines() if l.strip()]):
                 error_msg = "Parsing resulted in no items (all lines might be excluded or comments)."
             elif map_text.strip():
                  error_msg = "Parsing resulted in no items (check format and content)."
             else:
                  error_msg = "Map input is empty."
    except Exception as parse_e:
        error_msg = f"Error during map parsing: {parse_e}"
        print(f"ERROR: Exception during map parsing: {parse_e}")
        traceback.print_exc()

    if error_msg: return error_msg, False, None
    # It's possible parsing yields an empty list legitimately if all lines were excluded.
    # Handle this case before calling creation logic.
    if not parsed_items: return "Parsing resulted in no items to create (possibly all excluded or comments).", False, None

    # --- Structure Creation Step ---
    try:
        # Pass the parsed items (which might be empty if all lines were excluded)
        return create_structure_from_parsed(parsed_items, base_dir_str, queue=queue)
    except Exception as create_e:
        print(f"ERROR: Unexpected exception calling create_structure_from_parsed: {create_e}")
        traceback.print_exc()
        return f"Fatal error calling structure creation: {create_e}", False, None

def create_structure_from_parsed(parsed_items: List[Tuple[int, str, bool]], base_dir_str: str,
                                 queue: Optional[Any] = None) -> Tuple[str, bool, Optional[str]]:
    """
    Creates directory structure from parsed items list.
    Returns tuple: (message, success_bool, created_root_name_str or None)
    """
    base_dir = Path(base_dir_str).resolve()
    if not base_dir.is_dir():
        return f"Error: Base directory '{base_dir_str}' is not valid or accessible.", False, None

    path_stack: List[Path] = [base_dir] # Stack holds parent Path objects for current level
    created_root_name: Optional[str] = None
    total_items = len(parsed_items)
    item_name_for_error = "<No Items Parsed>" # For error reporting

    # --- Handle Empty Input Gracefully ---
    if not parsed_items:
         # This case should ideally be caught by the caller, but handle defensively
         return "No parsed items provided to create structure.", False, None

    try:
        # --- Validate First Item ---
        first_level, first_name, first_is_dir = parsed_items[0]
        if first_level != 0:
            raise ValueError(f"Map must start at level 0, but first item '{first_name}' is at level {first_level}.")
        if not first_is_dir:
            raise ValueError(f"Map must start with a directory, but first item '{first_name}' is not a directory.")

        # --- Process Items ---
        for i, (current_level, item_name, is_directory) in enumerate(parsed_items):
            item_name_for_error = item_name # Update for error context
            if queue: # Send progress update
                queue.put({'type': 'progress', 'current': i + 1, 'total': total_items})

            # --- Manage Path Stack ---
            # Target stack length for this item's *parent* is current_level + 1
            # (Base dir is level -1 essentially, stack[0])
            # Item at level 0 -> parent is stack[0] (base_dir) -> stack len = 1
            # Item at level 1 -> parent is stack[1] (level 0 dir) -> stack len = 2
            target_stack_len = current_level + 1
            # Pop levels off the stack until we are at the parent level
            while len(path_stack) > target_stack_len:
                path_stack.pop()

            # --- Indentation/Structure Consistency Check ---
            if len(path_stack) != target_stack_len:
                # This indicates a jump in indentation (e.g., level 0 then level 2)
                parent_level_available = len(path_stack) - 1
                raise ValueError(
                    f"Structure Error for item '{item_name}' at level {current_level}. "
                    f"Inconsistent indentation detected. Expected parent at level {current_level - 1}, "
                    f"but current stack depth only corresponds to level {parent_level_available}. "
                    f"Check map indentation near this item (possible jump from level {parent_level_available} to {current_level})."
                )

            current_parent_path = path_stack[-1] # Parent is the last path on the stack

            # --- Sanitize Item Name for Filesystem ---
            # Remove potentially problematic characters
            safe_item_name = re.sub(r'[<>:"/\\|?*]', '_', item_name)
            # Remove leading/trailing dots and spaces (problematic on Windows)
            safe_item_name = safe_item_name.strip('. ')
            if not safe_item_name:
                 # Handle cases where sanitization results in an empty name
                 safe_item_name = f"_sanitized_empty_name_{i+1}" # Use 1-based index for user message
                 print(f"Warning: Item '{item_name}' (line approx {i+1}) resulted in empty name after sanitization, using '{safe_item_name}'.")

            current_path = current_parent_path / safe_item_name

            # Store the name of the first created item (the root of the map structure)
            if i == 0:
                created_root_name = safe_item_name

            # --- Create File or Directory ---
            if is_directory:
                # Create the directory, including any necessary parent directories (idempotent)
                current_path.mkdir(parents=True, exist_ok=True)
                # Push this new directory onto the stack for its potential children
                path_stack.append(current_path)
            else:
                # Ensure the file's parent directory exists (idempotent)
                current_path.parent.mkdir(parents=True, exist_ok=True)
                # Create the empty file (or update timestamp if it exists)
                current_path.touch(exist_ok=True)

    except ValueError as ve:
        # Specific errors raised due to map structure issues
        return f"Error processing structure: {ve}", False, None
    except OSError as oe:
        # Filesystem related errors (permissions, invalid paths after sanitization etc.)
        print(f"ERROR in create_structure_from_parsed loop: OSError processing item '{item_name_for_error}' at path '{current_path}': {oe}")
        traceback.print_exc()
        return f"Filesystem error creating item '{item_name_for_error}': {oe}", False, None
    except Exception as e:
        # Catch any other unexpected errors
        print(f"ERROR in create_structure_from_parsed loop: Unhandled Exception processing item '{item_name_for_error}': {e}")
        traceback.print_exc()
        return f"Unexpected error creating structure near item '{item_name_for_error}': {e}", False, None

    # --- Final Success ---
    if queue: # Ensure progress reaches 100%
        queue.put({'type': 'progress', 'current': total_items, 'total': total_items})

    # Determine final message based on whether a root name was established
    final_root_name = created_root_name if created_root_name else "_structure_ (empty or root excluded?)"
    return f"Structure for '{final_root_name}' successfully created in '{base_dir}'", True, created_root_name

# ============================================================
# --- Parsing Logic (Orchestrator, Detector, Parsers) ---
# ============================================================
def parse_map(map_text: str, format_hint: str, excluded_lines: Optional[Set[int]] = None) -> Optional[List[Tuple[int, str, bool]]]:
    """
    Orchestrates parsing based on format hint or auto-detection.
    Handles excluded lines.
    Returns: List of (level, name, is_directory) tuples, or None on failure.
             Returns an empty list if input is valid but all lines are excluded/comments.
    """
    if excluded_lines is None: excluded_lines = set()

    actual_format = format_hint
    if format_hint == "Auto-Detect":
        actual_format = _detect_format(map_text)
        # print(f"Info: Auto-detected format as: '{actual_format}'") # Keep commented unless debugging
        if actual_format == "Unknown":
             print("Warning: Could not reliably detect format. Attempting Generic parser.")
             actual_format = "Generic" # Fallback to generic if detection fails

    # Select the appropriate parsing function based on the determined format
    parser_func = None
    if actual_format == "Spaces (2)":
        parser_func = lambda text, excludes: _parse_indent_based(text, excludes, spaces_per_level=2)
    elif actual_format == "Spaces (4)":
        parser_func = lambda text, excludes: _parse_indent_based(text, excludes, spaces_per_level=4)
    elif actual_format == "Tabs":
        parser_func = lambda text, excludes: _parse_indent_based(text, excludes, use_tabs=True)
    elif actual_format == "Tree":
        parser_func = _parse_tree_format # Uses revised tree logic
    elif actual_format == "Generic":
        parser_func = _parse_generic_indent # Fallback using older helper
    else:
        # Should not happen if auto-detect falls back to Generic or Unknown->Generic
        print(f"Error: Unknown format '{actual_format}' specified. Cannot parse.")
        return None

    # Call the selected parser function
    if parser_func:
        try:
            parsed_result = parser_func(map_text, excluded_lines)
            # Parser functions should return [] if valid but empty, None on error.
            return parsed_result
        except Exception as e:
            print(f"Error: Exception during call to parser for format '{actual_format}': {e}")
            traceback.print_exc()
            return None # Indicate failure
    else:
        # This case should also not be reachable normally
        print(f"Error: No parser function could be assigned for format '{actual_format}'.")
        return None

def _detect_format(map_text: str, sample_lines: int = 25) -> str:
    """
    Analyzes the first few lines of map_text to detect the format.
    Returns one of: "Tree", "Tabs", "Spaces (4)", "Spaces (2)", "Generic", "Unknown".
    """
    lines = map_text.strip().splitlines()
    # Consider only lines with some non-whitespace content for detection
    non_empty_lines = [line for line in lines if line.strip()][:sample_lines]

    if not non_empty_lines:
        return "Generic" # Treat empty or whitespace-only input as Generic

    # --- Tree Detection ---
    # Check for explicit tree prefixes (more reliable)
    # Need to check after potential leading whitespace
    has_tree_prefix = any(TREE_PREFIX_RE.match(line) for line in non_empty_lines)
    if has_tree_prefix:
        return "Tree"
    # Fallback: Check for structure characters anywhere might be too broad, stick to prefixes.

    # --- Tab Detection ---
    # Check if any non-empty, non-whitespace line *starts* with a tab
    if any(line.startswith('\t') for line in non_empty_lines if line and not line.isspace()):
        return "Tabs"

    # --- Space Indentation Detection ---
    # Collect leading space counts from lines that are indented with spaces
    space_indented_lines = [line for line in non_empty_lines if line and not line.isspace() and line[0] == ' ']
    leading_spaces = [len(line) - len(line.lstrip(' ')) for line in space_indented_lines]
    # Get unique positive indentation values found
    space_indents = sorted(list(set(sp for sp in leading_spaces if sp > 0)))

    if not space_indents:
        # No space-indented lines found among non-empty lines (could be all level 0, or tabs/tree missed)
        # If no tabs/tree detected either, fall back to Generic
        return "Generic"

    # Check for consistency based on common indent levels (4 or 2)
    if all(s % 4 == 0 for s in space_indents):
        return "Spaces (4)"
    if all(s % 2 == 0 for s in space_indents):
        # This catches multiples of 2, including 4. Check 4 first.
        return "Spaces (2)"

    # If indentation exists but isn't consistently divisible by 2 or 4, treat as generic
    return "Generic"

# --- Specific Parser Implementations ---
def _parse_indent_based(map_text: str, excluded_lines: Set[int],
                        spaces_per_level: Optional[int] = None, use_tabs: bool = False) -> Optional[List[Tuple[int, str, bool]]]:
    """ Parses map text using consistent space or tab indentation. """
    if not ((spaces_per_level is not None and spaces_per_level > 0) or use_tabs):
        print("Error (_parse_indent_based): Invalid arguments - need spaces_per_level or use_tabs=True.")
        return None # Invalid arguments

    lines = map_text.splitlines()
    parsed_items: List[Tuple[int, str, bool]] = []
    indent_unit = 1 if use_tabs else spaces_per_level
    if indent_unit is None or indent_unit <= 0: # Should be caught above, but double check
         print("Error (_parse_indent_based): Indent unit is invalid.")
         return None

    expected_level = 0 # Track expected level to detect inconsistencies

    for line_num, line in enumerate(lines, start=1):
        if line_num in excluded_lines:
            continue # Skip excluded lines

        components = _extract_line_components(line) # Uses OLD helper, updated for emojis
        if components.is_empty_or_comment:
            continue # Skip empty lines and comments

        # Determine leading characters count based on mode (tabs or spaces)
        if use_tabs:
            leading_chars_count = len(line) - len(line.lstrip('\t'))
        else:
            leading_chars_count = components.raw_indent_width # Use space count

        current_level = -1
        # Check for exact divisibility by the indent unit
        if leading_chars_count == 0:
             current_level = 0
        elif leading_chars_count > 0 and indent_unit > 0 and leading_chars_count % indent_unit == 0:
            current_level = leading_chars_count // indent_unit
        else:
            # Indentation doesn't match the expected unit for this format
            print(f"Warning (_parse_indent_based): Skipping line {line_num} due to inconsistent indentation "
                  f"(leading chars: {leading_chars_count}, expected multiple of {indent_unit}). Line: '{line.rstrip()}'")
            continue # Skip lines with inconsistent indentation

        # --- Optional: Add more strict level checking ---
        # if current_level > expected_level:
        #     print(f"Warning (_parse_indent_based): Skipping line {line_num} due to level jump "
        #           f"(Current: {current_level}, Expected max: {expected_level}). Line: '{line.rstrip()}'")
        #     continue
        # expected_level = current_level + 1 # Next line can be at most one level deeper
        # --- End optional check ---


        item_name = components.clean_name
        is_directory = components.is_directory
        if not item_name:
             print(f"Warning (_parse_indent_based): Skipping line {line_num} as no item name found after parsing. Line: '{line.rstrip()}'")
             continue # Skip if parsing failed to find a name

        parsed_items.append((current_level, item_name, is_directory))

    # Final check: ensure the first item is at level 0 if items were parsed
    if parsed_items and parsed_items[0][0] != 0:
        print(f"Warning (_parse_indent_based): First parsed item '{parsed_items[0][1]}' is at level {parsed_items[0][0]} (expected 0). Structure might be incorrect.")
        # Depending on strictness, could return None here or allow it. Let's allow for now.

    return parsed_items # Return list (possibly empty)

def _parse_tree_format(map_text: str, excluded_lines: Set[int]) -> Optional[List[Tuple[int, str, bool]]]:
    """ (REVISED LOGIC) Parses tree-style formats by analyzing prefix structure. """
    lines = map_text.splitlines()
    parsed_items: List[Tuple[int, str, bool]] = []
    expected_level = 0 # Track expected level

    for line_num, line in enumerate(lines, start=1):
        original_line_rstrip = line.rstrip()
        if line_num in excluded_lines:
            continue
        # Skip empty lines and comments
        line_content = original_line_rstrip.strip()
        if not line_content or line_content.startswith('#'):
            continue

        current_level = 0
        name_remainder_index = 0 # Index in original_line_rstrip where content starts

        # --- Calculate Level based on Pipe/Space prefixes ---
        while True:
            segment = original_line_rstrip[name_remainder_index : name_remainder_index + TREE_LEVEL_UNIT_LEN]
            if segment == TREE_PIPE:
                current_level += 1
                name_remainder_index += TREE_LEVEL_UNIT_LEN
            elif segment == TREE_SPACE: # Also indicates a level, just under a 'last branch' parent
                current_level += 1
                name_remainder_index += TREE_LEVEL_UNIT_LEN
            else:
                # Stop when we don't see a standard pipe/space segment
                break

        # --- Identify Branch Prefix ---
        remainder_after_level = original_line_rstrip[name_remainder_index:]
        has_branch_prefix = False
        if remainder_after_level.startswith(TREE_BRANCH):
            name_remainder_index += len(TREE_BRANCH)
            has_branch_prefix = True
        elif remainder_after_level.startswith(TREE_LAST_BRANCH):
            name_remainder_index += len(TREE_LAST_BRANCH)
            has_branch_prefix = True
        # Allow lines without a branch prefix only if they are at level 0
        elif current_level == 0:
             pass # Level 0 items might not have a branch prefix
        else:
             # If not level 0 and no branch prefix found, it's likely a format error
             print(f"Warning (_parse_tree_format): Skipping line {line_num} due to missing tree branch prefix "
                   f"at level {current_level}. Line: '{original_line_rstrip}'")
             continue


        # --- Optional: Add more strict level checking ---
        # if current_level > expected_level:
        #      print(f"Warning (_parse_tree_format): Skipping line {line_num} due to level jump "
        #            f"(Current: {current_level}, Expected max: {expected_level}). Line: '{original_line_rstrip}'")
        #      continue
        # expected_level = current_level + 1
        # --- End optional check ---


        # --- Extract Final Components (Emoji, Name, Type) ---
        # Pass the remainder *after* the level and branch prefixes
        name_remainder = original_line_rstrip[name_remainder_index:]
        _emoji, item_name, is_directory = _extract_final_components(name_remainder, original_line_rstrip)

        if not item_name:
            # Check if it was just an empty directory marker like "└── /"
            if is_directory and name_remainder.strip() == '/':
                 print(f"Warning (_parse_tree_format): Line {line_num} seems to be an empty directory marker ('{original_line_rstrip}'). Skipping.")
            else:
                 print(f"Warning (_parse_tree_format): Skipping line {line_num} as no item name found after parsing prefixes. Remainder: '{name_remainder}' Line: '{original_line_rstrip}'")
            continue

        parsed_items.append((current_level, item_name, is_directory))

    # Final check: ensure the first item is at level 0 if items were parsed
    if parsed_items and parsed_items[0][0] != 0:
        print(f"Warning (_parse_tree_format): First parsed item '{parsed_items[0][1]}' is at level {parsed_items[0][0]} (expected 0). Structure might be incorrect.")
        # Allow for now, but could be made stricter.

    return parsed_items

def _parse_generic_indent(map_text: str, excluded_lines: Set[int]) -> Optional[List[Tuple[int, str, bool]]]:
    """ Parses based on generic indentation width changes (fallback). Uses OLD helper. """
    lines = map_text.splitlines()
    if not lines: return [] # Return empty list for empty input

    parsed_items: List[Tuple[int, str, bool]] = []
    # Maps indent width (int) to detected level (int)
    indent_map: Dict[int, int] = {0: 0} # Assume indent 0 is level 0
    # Stack to keep track of indent levels encountered for parent lookup
    level_stack: List[int] = [0] # Start with level 0 indent

    last_processed_level = -1 # Track the level of the previously added item

    for line_num, line in enumerate(lines, start=1):
        if line_num in excluded_lines:
            continue

        components = _extract_line_components(line) # Uses OLD helper, updated for emojis
        if components.is_empty_or_comment:
            continue

        # Use raw_indent_width (leading spaces) as the key for level determination
        indent_width = components.raw_indent_width
        current_level = -1

        # Determine level based on indent width changes
        if indent_width > level_stack[-1]:
            # Increase in indent means deeper level
            current_level = len(level_stack) # New level is current stack depth
            level_stack.append(indent_width)
            indent_map[indent_width] = current_level
        elif indent_width in indent_map:
            # Seen this indent before, find its level
            current_level = indent_map[indent_width]
            # Pop stack back to the parent level of this indent
            while level_stack[-1] > indent_width:
                 level_stack.pop()
            # Safety check: Ensure the indent found matches the top of the stack after popping
            if level_stack[-1] != indent_width:
                 print(f"Warning (_parse_generic_indent): Indentation logic inconsistency on line {line_num}. "
                       f"Indent {indent_width} found, but stack top is {level_stack[-1]} after popping. Line: '{line.rstrip()}'")
                 # Option: Skip line, or try to force level? Forcing might be risky. Skip.
                 continue
        else:
            # Decrease in indent, but not to a previously seen level - likely an error
            print(f"Warning (_parse_generic_indent): Skipping line {line_num} due to inconsistent indentation decrease. "
                  f"Indent width {indent_width} not previously mapped. Line: '{line.rstrip()}'")
            continue

        # --- Strict Level Progression Check ---
        # Allow same level or direct child level, reject jumps/invalid decreases
        if not (current_level == last_processed_level or \
                current_level == last_processed_level + 1):
             # Allow going back to *any* valid parent level if indent matches stack
             if indent_width in indent_map and current_level <= last_processed_level:
                  pass # Okay to return to a previous level
             else:
                  print(f"Warning (_parse_generic_indent): Skipping line {line_num} due to unexpected level change. "
                        f"From level {last_processed_level} to {current_level}. Line: '{line.rstrip()}'")
                  # Roll back stack change if we skip the line
                  if indent_width == level_stack[-1] and current_level == len(level_stack) - 1 :
                      level_stack.pop() # Remove the level we just added
                  continue


        item_name = components.clean_name
        is_directory = components.is_directory
        if not item_name:
            print(f"Warning (_parse_generic_indent): Skipping line {line_num} as no item name found after parsing. Line: '{line.rstrip()}'")
            continue

        parsed_items.append((current_level, item_name, is_directory))
        last_processed_level = current_level # Update last processed level

    # Final check: ensure the first item is at level 0 if items were parsed
    if parsed_items and parsed_items[0][0] != 0:
        print(f"Warning (_parse_generic_indent): First parsed item '{parsed_items[0][1]}' is at level {parsed_items[0][0]} (expected 0). Structure might be incorrect.")

    return parsed_items