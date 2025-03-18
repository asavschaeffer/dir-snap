from abc import ABC, abstractmethod

class BaseGenerator(ABC):
    """Base class for all directory structure generators."""
    
    @abstractmethod
    def generate(self, directory: str, **kwargs) -> str:
        """Generate the directory structure representation.
        
        Args:
            directory: The root directory path
            **kwargs: Additional arguments specific to each generator
            
        Returns:
            str: The generated representation
        """
        pass 