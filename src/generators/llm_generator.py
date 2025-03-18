import os
from .base import BaseGenerator

class LLMGenerator(BaseGenerator):
    """Generator for LLM-optimized text representation."""
    
    def generate(self, directory: str, **kwargs) -> str:
        """Generate a minimal text representation of the directory structure.
        Format: type|path
        Example: d|/root/folder f|/root/file.txt
        
        Args:
            directory: The root directory path
            **kwargs: Not used in this generator
            
        Returns:
            str: The generated text representation
        """
        def generate_text_tree(path: str) -> list[str]:
            """Generate a minimal text-based tree representation optimized for LLM consumption."""
            tree = []
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                rel_path = os.path.relpath(item_path, os.path.dirname(path))
                if os.path.isdir(item_path):
                    tree.append(f"d|{rel_path}")
                    tree.extend(generate_text_tree(item_path))
                else:
                    tree.append(f"f|{rel_path}")
            return tree
        
        return "\n".join(generate_text_tree(directory)) 