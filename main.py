"""main.py: The main entry point script for the application.

    Parse command-line arguments (like an initial path from the right-click context menu).
    Import the main application class from the dirmapper package.
    Instantiate and run the application's GUI loop."""
# main.py
import sys
import os
from pathlib import Path

# Ensure the 'dirmapper' package directory is findable if running main.py directly
# This might be needed depending on how the project is structured and run
script_dir = Path(__file__).parent
package_dir = script_dir / 'dirmapper'
if str(package_dir) not in sys.path:
     sys.path.insert(0, str(script_dir)) # Add project root to path

from dirmapper.app import DirMapperApp

if __name__ == "__main__":
    initial_path_str = None
    initial_mode = 'snapshot' # Default mode if launched without context

    # Very basic argument check: assumes the first argument is the path
    # Real context menu setups might pass specific flags too
    if len(sys.argv) > 1:
        potential_path = Path(sys.argv[1])
        # Check if the path exists and is a directory or file
        if potential_path.exists():
            initial_path_str = str(potential_path.resolve()) # Use resolved absolute path
            if potential_path.is_dir():
                initial_mode = 'snapshot' # Right-clicked a directory
                # TODO: Could add a check for a special flag like 'scaffold_here' later
            elif potential_path.is_file():
                initial_mode = 'scaffold_from_file' # Right-clicked a potential map file
        else:
            # Handle case where argument isn't a valid path?
            # Maybe treat it as text input? For now, ignore invalid paths.
            print(f"Warning: Argument '{sys.argv[1]}' is not a valid path. Starting normally.")
            pass

    # Instantiate and run the app
    try:
        app = DirMapperApp(initial_path=initial_path_str, initial_mode=initial_mode)
        app.mainloop()
    except Exception as e:
        # Basic error handling if app fails to initialize
        print(f"FATAL ERROR: Could not launch DirMapperApp.")
        print(e)
        # In a real app, might use a simple Tk messagebox for errors here too
        input("Press Enter to exit.") # Keep console open to see error