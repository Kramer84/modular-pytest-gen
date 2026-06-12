import ast
from pathlib import Path
from typing import Dict, Union


class ImportResolver:
    """
    Scans the target project's source tree to build a mapping of physical 
    file paths to their fully qualified, logical import paths.
    """
    def __init__(self, source_root: Union[str, Path], import_prefix: str):
        # FIX: Resolve paths strictly to prevent relative vs absolute matching errors
        self.source_root = Path(source_root).resolve()
        self.import_prefix = import_prefix
        
        # Map physical path -> logical module path
        self.physical_to_logical: Dict[str, str] = {}
        
        # 2D Map: physical_file_path -> object_name -> public_import_path
        # Prevents overwriting aliases across submodules (e.g., otaf.api.Client vs otaf.db.Client)
        self.public_aliases: Dict[str, Dict[str, str]] = {}
        
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
                
            # Avoid duplicating the import prefix if it's already the top-level directory
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

        # Iterate strictly over top-level body nodes, not ast.walk(), to avoid catching local function imports
        for node in tree.body:
            # Generic Python mechanism: `from ._assembly_modeling import GapMatrix`
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    # Absolute import resolution
                    if not node.module:
                        continue
                        
                    module_parts = node.module.split(".")
                    base_path = self.source_root
                    
                    # Determine if the import_prefix is a physical folder or a virtual namespace
                    if self.import_prefix and module_parts[0] == self.import_prefix:
                        if not (self.source_root / module_parts[0]).exists():
                            module_parts.pop(0)  # Strip virtual prefix to map correctly
                            
                    base_path = base_path.joinpath(*module_parts)
                    
                else:
                    # Relative import resolution
                    target_dir = file_path.parent
                    for _ in range(node.level - 1):
                        if target_dir.parent == target_dir:
                            break
                        target_dir = target_dir.parent
                        
                    if node.module:
                        base_path = target_dir.joinpath(*node.module.split("."))
                    else:
                        base_path = target_dir
                        
                # Resolve file vs directory
                for alias in node.names:
                    target_entity = base_path if node.module else base_path / alias.name
                    
                    if target_entity.is_dir():
                        target_file = target_entity / "__init__.py"
                    else:
                        target_file = target_entity.with_suffix(".py")
                        
                    target_file_str = str(target_file)
                    if target_file_str not in self.public_aliases:
                        self.public_aliases[target_file_str] = {}
                        
                    self.public_aliases[target_file_str][alias.name] = f"{current_logical_path}.{alias.name}"
                    
            # Bespoke OTAF mechanism: `_reexports = {"GapMatrix": "_assembly_modeling"}`
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_reexports":
                        if isinstance(node.value, ast.Dict):
                            for key, val in zip(node.value.keys, node.value.values):
                                if isinstance(key, ast.Constant) and isinstance(val, ast.Constant):
                                    obj_name = str(key.value)
                                    source_mod = str(val.value)
                                    
                                    # Handle directory vs file for OTAF re-exports
                                    base_path = file_path.parent / source_mod
                                    if base_path.is_dir():
                                        target_file = base_path / "__init__.py"
                                    else:
                                        target_file = base_path.with_suffix(".py")
                                        
                                    target_file_str = str(target_file)
                                    
                                    if target_file_str not in self.public_aliases:
                                        self.public_aliases[target_file_str] = {}
                                        
                                    self.public_aliases[target_file_str][obj_name] = f"{current_logical_path}.{obj_name}"

    def get_import_path(self, physical_file: Union[str, Path], object_name: str) -> str:
        """
        Determines the most accurate import statement for a given function or class.
        Prefers public aliases if exposed via __init__, otherwise falls back to the physical module.
        """
        # FIX: Resolve physical paths strictly
        physical_file_str = str(Path(physical_file).resolve())

        # Check the 2D mapping to see if this specific object from this specific file was exposed
        if physical_file_str in self.public_aliases and object_name in self.public_aliases[physical_file_str]:
            return self.public_aliases[physical_file_str][object_name]
            
        # Otherwise, fall back to its exact physical module location
        logical_mod = self.physical_to_logical.get(physical_file_str)
        if not logical_mod:
            raise ValueError(f"File {physical_file_str} is outside the known source tree.")
            
        return f"{logical_mod}.{object_name}"