import os
from .base import BaseGenerator

class DiagramGenerator(BaseGenerator):
    """Generator for visual diagram representation."""
    
    def generate(self, directory: str, **kwargs) -> str:
        """Generate a visual diagram representation of the directory structure.
        
        Args:
            directory: The root directory path
            **kwargs: Additional arguments:
                - max_depth: Maximum depth to traverse (default: 3)
                - max_items_per_dir: Maximum items to show per directory (default: 5)
                - diagram_type: Type of diagram (default: "mindmap")
                
        Returns:
            str: The generated diagram representation
        """
        max_depth = kwargs.get('max_depth', 3)
        max_items_per_dir = kwargs.get('max_items_per_dir', 5)
        diagram_type = kwargs.get('diagram_type', 'mindmap')
        
        # Initialize diagram based on type
        if diagram_type == 'mindmap':
            self.diagram = "mindmap\n"
            root_node = f"root((📁 {os.path.basename(directory)}))"
        else:
            direction = "TD" if "TD" in diagram_type else "LR"
            self.diagram = f"graph {direction}\n"
            root_node = f"root[📁 {os.path.basename(directory)}]"
        
        self.diagram += root_node + "\n"
        
        def add_subtree(path: str, parent_id: str, depth: int = 0, prefix: str = "") -> None:
            """Recursively add items to the diagram."""
            if depth >= max_depth:
                self.diagram += f"{prefix}{parent_id} --> {parent_id}_depth[⋯]\n"
                return
                
            try:
                items = sorted(os.listdir(path))
                # Limit items per directory
                items = items[:max_items_per_dir]
                
                for i, item in enumerate(items):
                    item_path = os.path.join(path, item)
                    item_id = f"{parent_id}_{i}"
                    
                    if os.path.isdir(item_path):
                        if "mindmap" in diagram_type:
                            self.diagram += f"{prefix}{parent_id} --> {item_id}((📁 {item}))\n"
                        else:
                            self.diagram += f"{prefix}{parent_id} --> {item_id}[📁 {item}]\n"
                        add_subtree(item_path, item_id, depth + 1, prefix + "  ")
                    else:
                        if "mindmap" in diagram_type:
                            self.diagram += f"{prefix}{parent_id} --> {item_id}((📄 {item}))\n"
                        else:
                            self.diagram += f"{prefix}{parent_id} --> {item_id}[📄 {item}]\n"
                
                # Add ellipsis if there are more items
                if len(os.listdir(path)) > max_items_per_dir:
                    ellipsis_id = f"{parent_id}_more"
                    if "mindmap" in diagram_type:
                        self.diagram += f"{prefix}{parent_id} --> {ellipsis_id}((⋯))\n"
                    else:
                        self.diagram += f"{prefix}{parent_id} --> {ellipsis_id}[⋯]\n"
                        
            except PermissionError:
                error_id = f"{parent_id}_error"
                if "mindmap" in diagram_type:
                    self.diagram += f"{prefix}{parent_id} --> {error_id}((⚠️ Permission Denied))\n"
                else:
                    self.diagram += f"{prefix}{parent_id} --> {error_id}[⚠️ Permission Denied]\n"
        
        add_subtree(directory, "root")
        return self.diagram 