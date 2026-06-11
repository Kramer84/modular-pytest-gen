import ast
from pathlib import Path
from typing import Dict, Union


class ImportResolver:
    """
    Scans the target project's source tree to build a mapping of physical 
    file paths to their fully qualified, logical import paths.
    """
    def __init__(self, source_root: Union[str, Path], import_prefix: str):
        self.source_root = Path(source_root)
        self.import_prefix = import_prefix
        
        # Map physical path -> logical module path
        # e.g., src/otaf/_assembly_modeling.py -> otaf._assembly_modeling
        self.physical_to_logical: Dict[str, str] = {}
        
        # Map object name -> public import path
        # e.g., GapMatrix -> otaf.GapMatrix
        self.public_aliases: Dict[str, str] = {}
        
        self._build_tree()

    def _build_tree(self):
        """Walks the source directory to build the namespace mapping."""
        if not self.source_root.exists():
            return

        for file_path in self.source_root.rglob("*.py"):
            # 1. Resolve logical module paths
            rel_path = file_path.relative_to(self.source_root)
            parts = list(rel_path.parts)
            parts[-1] = parts[-1].replace(".py", "")
            
            if parts[-1] == "__init__":
                parts.pop()
                
            # FIX: Avoid duplicating the import prefix if it's already the top-level directory
            # Also gracefully handle the edge case where import_prefix is an empty string
            if self.import_prefix:
                if parts and parts[0] == self.import_prefix:
                    logical_path = ".".join(parts)
                else:
                    logical_path = ".".join([self.import_prefix] + parts) if parts else self.import_prefix
            else:
                logical_path = ".".join(parts)
                
            self.physical_to_logical[str(file_path)] = logical_path

            # 2. Parse __init__.py files for re-exports and aliases
            if file_path.name == "__init__.py":
                self._parse_init(file_path, logical_path)

    def _parse_init(self, file_path: Path, current_logical_path: str):
        """Extracts standard imports and bespoke OTAF dictionaries to find public aliases."""
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Generic Python mechanism: `from ._assembly_modeling import GapMatrix`
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    # We map the imported object to this __init__'s public namespace
                    self.public_aliases[alias.name] = f"{current_logical_path}.{alias.name}"
                    
            # Bespoke OTAF mechanism: `_reexports = {"GapMatrix": "_assembly_modeling"}`
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_reexports":
                        if isinstance(node.value, ast.Dict):
                            for key in node.value.keys:
                                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                    self.public_aliases[key.value] = f"{current_logical_path}.{key.value}"

    def get_import_path(self, physical_file: Union[str, Path], object_name: str) -> str:
        """
        Determines the most accurate import statement for a given function or class.
        Prefers public aliases if exposed via __init__, otherwise falls back to the physical module.
        """
        physical_file_str = str(Path(physical_file))

        # If the object was explicitly re-exported, use the public API path
        if object_name in self.public_aliases:
            return self.public_aliases[object_name]
            
        # Otherwise, fall back to its exact physical module location
        logical_mod = self.physical_to_logical.get(physical_file_str)
        if not logical_mod:
            raise ValueError(f"File {physical_file_str} is outside the known source tree.")
            
        return f"{logical_mod}.{object_name}"