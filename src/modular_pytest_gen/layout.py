from pathlib import Path
from typing import Union
from .config import ProjectConfig

class LayoutManager:
    """
    Determines the correct output path for generated test files based on 
    the user's layout configuration (adjacent vs external, flat vs nested).
    """
    def __init__(self, config: ProjectConfig):
        self.config = config

    def get_test_file_path(self, source_file_path: Union[str, Path]) -> Path:
        source_path = Path(source_file_path)
        if not source_path.name.endswith(".py"):
            raise ValueError(f"Source path must be a Python file: {source_path}")

        # Prefix the original filename with 'test_'
        test_filename = f"test_{source_path.name}"
        
        strategy = self.config.layout.strategy.lower()
        
        if strategy == "adjacent":
            return source_path.parent / test_filename
            
        elif strategy == "external":
            test_root = Path(self.config.layout.test_root)
            structure = self.config.layout.structure.lower()
            
            if structure == "flat":
                return test_root / test_filename
                
            elif structure == "nested":
                source_root = Path(self.config.source_root)
                try:
                    # Attempt to find the path relative to the defined source root
                    relative_dir = source_path.parent.relative_to(source_root)
                    return test_root / relative_dir / test_filename
                except ValueError:
                    # If the source file is somehow outside the source_root, 
                    # fallback to dropping it directly into the test root to prevent crashes.
                    return test_root / test_filename
            else:
                raise ValueError(f"Unknown layout structure: '{structure}'. Must be 'flat' or 'nested'.")
        else:
            raise ValueError(f"Unknown layout strategy: '{strategy}'. Must be 'adjacent' or 'external'.")