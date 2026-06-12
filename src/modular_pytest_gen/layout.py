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
        
        strategy = self.config.layout.strategy.lower()
        
        if strategy == "adjacent":
            return source_path.parent / f"test_{source_path.name}"
            
        elif strategy == "external":
            test_root = Path(self.config.layout.test_root)
            structure = self.config.layout.structure.lower()
            source_root = Path(self.config.source_root)
            
            try:
                relative_dir = source_path.parent.relative_to(source_root)
            except ValueError:
                # Fallback to flattening the absolute path to prevent collisions
                safe_prefix = str(source_path.parent.resolve()).replace("/", "_").replace("\\", "_").strip("_")
                return test_root / f"test_external_{safe_prefix}_{source_path.name}"
                
            if structure == "flat":
                # Prevent namespace collisions by injecting the relative path into the filename
                if str(relative_dir) == ".":
                    flat_name = f"test_{source_path.name}"
                else:
                    prefix = str(relative_dir).replace("/", "_").replace("\\", "_")
                    flat_name = f"test_{prefix}_{source_path.name}"
                return test_root / flat_name
                
            elif structure == "nested":
                return test_root / relative_dir / f"test_{source_path.name}"
            else:
                raise ValueError(f"Unknown layout structure: '{structure}'. Must be 'flat' or 'nested'.")
        else:
            raise ValueError(f"Unknown layout strategy: '{strategy}'. Must be 'adjacent' or 'external'.")