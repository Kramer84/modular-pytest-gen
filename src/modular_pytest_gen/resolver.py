import ast
from pathlib import Path
from typing import Any, Dict, Set, Union


class ImportResolver:
    def __init__(self, source_root: Union[str, Path], import_prefix: str):

        self.source_root = Path(source_root).resolve()
        self.import_prefix = import_prefix
        self.physical_to_logical: Dict[str, str] = {}
        self.public_aliases: Dict[str, Dict[str, str]] = {}
        self.file_definitions: Dict[str, Set[str]] = {}
        self._build_tree()

    def __repr__(self) -> str:

        return f"ImportResolver(source_root={self.source_root!r}, import_prefix={self.import_prefix!r}, files_mapped={len(self.physical_to_logical)}, aliases_found={len(self.public_aliases)})"

    def _get_file_definitions(self, file_path: Path) -> Set[str]:

        definitions: Set[str] = set()
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    definitions.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            definitions.add(target.id)
        except Exception:
            pass
        return definitions

    def _build_tree(self):

        if not self.source_root.exists():
            return
        all_files = list(self.source_root.rglob("*.py"))
        for file_path in all_files:
            file_path_resolved = file_path.resolve()
            rel_path = file_path_resolved.relative_to(self.source_root)
            parts = list(rel_path.parts)
            parts[-1] = parts[-1].replace(".py", "")
            if parts[-1] == "__init__":
                parts.pop()
            if self.import_prefix:
                if parts and parts[0] == self.import_prefix:
                    logical_path = ".".join(parts)
                else:
                    logical_path = (
                        ".".join([self.import_prefix] + parts)
                        if parts
                        else self.import_prefix
                    )
            else:
                logical_path = ".".join(parts)
            file_str = str(file_path_resolved)
            self.physical_to_logical[file_str] = logical_path
            self.file_definitions[file_str] = self._get_file_definitions(
                file_path_resolved
            )
        init_files = [f for f in all_files if f.name == "__init__.py"]
        init_files.sort(key=lambda p: len(p.parts), reverse=True)
        for file_path in init_files:
            file_path_resolved = file_path.resolve()
            logical_path = self.physical_to_logical[str(file_path_resolved)]
            self._parse_init(file_path_resolved, logical_path)

    def _parse_init(self, file_path: Path, current_logical_path: str):

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            return
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    if not node.module:
                        continue
                    module_parts = node.module.split(".")
                    base_path = self.source_root
                    if self.import_prefix and module_parts[0] == self.import_prefix:
                        if not (self.source_root / module_parts[0]).exists():
                            module_parts.pop(0)
                    base_path = base_path.joinpath(*module_parts)
                else:
                    target_dir = file_path.parent
                    for _ in range(node.level - 1):
                        if target_dir.parent == target_dir:
                            break
                        target_dir = target_dir.parent
                    base_path = (
                        target_dir.joinpath(*node.module.split("."))
                        if node.module
                        else target_dir
                    )
                for alias in node.names:
                    if alias.name == "*":
                        target_file = (
                            base_path
                            if base_path.is_file()
                            else base_path.with_suffix(".py")
                        )
                        if not target_file.exists() and base_path.is_dir():
                            target_file = base_path / "__init__.py"
                        target_str = str(target_file.resolve())
                        if target_str in self.file_definitions:
                            for name in self.file_definitions[target_str]:
                                self.public_aliases.setdefault(target_str, {})[name] = (
                                    f"{current_logical_path}.{name}"
                                )
                    else:
                        potential_file = (base_path / alias.name).with_suffix(".py")
                        potential_dir = base_path / alias.name
                        if potential_file.exists() or (
                            potential_dir.is_dir()
                            and (potential_dir / "__init__.py").exists()
                        ):
                            actual_target = (
                                potential_file
                                if potential_file.exists()
                                else potential_dir / "__init__.py"
                            )
                            target_str = str(actual_target.resolve())
                            exposed_mod_name = (
                                alias.asname if alias.asname else alias.name
                            )
                            if target_str in self.file_definitions:
                                for name in self.file_definitions[target_str]:
                                    self.public_aliases.setdefault(target_str, {})[
                                        name
                                    ] = f"{current_logical_path}.{exposed_mod_name}.{name}"
                        else:
                            target_file = (
                                base_path
                                if base_path.is_file()
                                else base_path.with_suffix(".py")
                            )
                            if not target_file.exists() and base_path.is_dir():
                                target_file = base_path / "__init__.py"
                            target_str = str(target_file.resolve())
                            exposed_obj_name = (
                                alias.asname if alias.asname else alias.name
                            )
                            self.public_aliases.setdefault(target_str, {})[
                                alias.name
                            ] = f"{current_logical_path}.{exposed_obj_name}"
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_reexports":
                        if isinstance(node.value, ast.Dict):
                            for key, val in zip(node.value.keys, node.value.values):
                                if isinstance(key, ast.Constant) and isinstance(
                                    val, ast.Constant
                                ):
                                    obj_name = str(key.value)
                                    source_mod = str(val.value)
                                    base_path = file_path.parent / source_mod
                                    target_file = (
                                        base_path / "__init__.py"
                                        if base_path.is_dir()
                                        else base_path.with_suffix(".py")
                                    )
                                    target_str = str(target_file.resolve())
                                    self.public_aliases.setdefault(target_str, {})[
                                        obj_name
                                    ] = f"{current_logical_path}.{obj_name}"

    def get_import_path(self, physical_file: Union[str, Path], object_name: str) -> str:

        physical_file_str = str(Path(physical_file).resolve())
        if (
            physical_file_str in self.public_aliases
            and object_name in self.public_aliases[physical_file_str]
        ):
            return self.public_aliases[physical_file_str][object_name]
        logical_mod = self.physical_to_logical.get(physical_file_str)
        if not logical_mod:
            raise ValueError(
                f"File {physical_file_str} is outside the known source tree."
            )
        return f"{logical_mod}.{object_name}"
