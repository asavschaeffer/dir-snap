# filename: dirSnap/utils.py
""" utils.py: Contains helper functions or constants that might be shared across modules. """
import sys
import os
from pathlib import Path

# --- Constants ---
# (Keep existing constants like DEFAULT_IGNORE_PATTERNS if they were moved here,
# otherwise define application name)
APP_NAME = "DirSnap"
CONFIG_FILENAME = "config.json"

# --- Configuration File Helper ---

def get_config_dir() -> Path:
    """
    Determines the platform-specific user configuration directory for the application.

    Returns:
        Path: The path to the configuration directory.
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%\AppName
        appdata = os.getenv('APPDATA')
        if appdata:
            config_dir = Path(appdata) / APP_NAME
        else:
            # Fallback if APPDATA is not set (unlikely)
            config_dir = Path.home() / f".{APP_NAME}"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/AppName
        config_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux/Other POSIX: ~/.config/AppName (preferred) or ~/.AppName (fallback)
        xdg_config_home = os.getenv('XDG_CONFIG_HOME')
        if xdg_config_home:
            config_dir = Path(xdg_config_home) / APP_NAME
        else:
            # Fallback based on XDG Base Directory Specification
            config_dir = Path.home() / ".config" / APP_NAME

    return config_dir

def get_config_path() -> Path:
    """
    Gets the full path to the configuration file, ensuring the directory exists.

    Returns:
        Path: The full path to the config.json file.
    """
    config_dir = get_config_dir()
    # Ensure the directory exists
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Handle potential permission errors or other issues creating the directory
        print(f"Warning: Could not create config directory '{config_dir}'. Using fallback in home directory. Error: {e}")
        config_dir = Path.home() / f".{APP_NAME}_config" # Fallback path
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as fallback_e:
            print(f"FATAL: Could not create fallback config directory '{config_dir}'. Error: {fallback_e}")
            # In a real app, might raise the exception or exit gracefully
            # For now, we'll just return the path and let file operations fail later
            pass # Allow returning the path even if creation failed

    return config_dir / CONFIG_FILENAME