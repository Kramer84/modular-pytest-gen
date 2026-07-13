import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Set


class ModuleParser:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()
        self.tree = ast.parse(self.source_code)

    def parse(self) -> Dict[str, Any]:
        import_registry: Dict[str, Dict[str, Any]] = {}
        free_floating_registry: Dict[str, str] = {}
        internal_sibling_registry: Dict[str, str] = {}
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    import_registry[local_name] = {
                        "type": "absolute",
                        "module": alias.name,
                        "alias": alias.asname,
                    }
            elif isinstance(node, ast.ImportFrom):
                if not node.module:
                    continue
                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    import_registry[local_name] = {
                        "type": "from",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                    }
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                internal_sibling_registry[node.name] = ast.unparse(node)
            elif isinstance(node, ast.ClassDef):
                internal_sibling_registry[node.name] = ast.unparse(node)
            elif isinstance(node, ast.If) and self._is_main_boilerplate(node):
                continue
            else:
                node_code = ast.unparse(node)
                defined_names = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                defined_names.add(target.id)
                    elif isinstance(child, ast.AnnAssign):
                        if isinstance(child.target, ast.Name):
                            defined_names.add(child.target.id)
                for name in defined_names:
                    free_floating_registry[name] = node_code
        analysis: Dict[str, Any] = {
            "filename": self.file_path.name,
            "module_docstring": ast.get_docstring(self.tree),
            "dunder_all": None,
            "constants": {},
            "exceptions": [],
            "classes": [],
            "functions": [],
            "free_floating_code": list(set(free_floating_registry.values())),
            "flags": {
                "has_dunder_all": False,
                "has_free_floating_code": False,
                "profile": "UNKNOWN",
            },
        }
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                immediate_names: Set[str] = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        immediate_names.add(child.id)
                    if hasattr(child, "annotation") and child.annotation:
                        for ann_child in ast.walk(child.annotation):
                            if isinstance(ann_child, ast.Name):
                                immediate_names.add(ann_child.id)
                extended_used_names = set(immediate_names)
                matched_free_code = set()
                names_to_check = list(immediate_names)
                checked_names = set()
                while names_to_check:
                    current_name = names_to_check.pop(0)
                    if current_name in checked_names:
                        continue
                    checked_names.add(current_name)
                    if current_name in free_floating_registry:
                        block_code = free_floating_registry[current_name]
                        matched_free_code.add(block_code)
                        try:
                            for sub_child in ast.walk(ast.parse(block_code)):
                                if isinstance(sub_child, ast.Name):
                                    extended_used_names.add(sub_child.id)
                                    names_to_check.append(sub_child.id)
                        except Exception:
                            pass
                    if (
                        current_name in internal_sibling_registry
                        and current_name != node.name
                    ):
                        sibling_code = internal_sibling_registry[current_name]
                        sibling_block = f"# Sibling dependency defined in this module:\n{sibling_code}"
                        matched_free_code.add(sibling_block)
                        try:
                            for sub_child in ast.walk(ast.parse(sibling_code)):
                                if isinstance(sub_child, ast.Name):
                                    extended_used_names.add(sub_child.id)
                                    names_to_check.append(sub_child.id)
                        except Exception:
                            pass
                matched_imports = []
                for name in extended_used_names:
                    if name in import_registry:
                        meta = import_registry[name]
                        if meta["type"] == "absolute":
                            stmt = f"import {meta['module']}"
                            if meta["alias"]:
                                stmt += f" as {meta['alias']}"
                            matched_imports.append(stmt)
                        elif meta["type"] == "from":
                            stmt = f"from {'.' * meta['level']}{meta['module']} import {meta['name']}"
                            if meta["alias"]:
                                stmt += f" as {meta['alias']}"
                            matched_imports.append(stmt)
                matched_free_code = set()
                for name in extended_used_names:
                    if name in free_floating_registry:
                        matched_free_code.add(free_floating_registry[name])
                    if name in internal_sibling_registry and name != node.name:
                        sibling_block = f"# Sibling dependency defined in this module:\n{internal_sibling_registry[name]}"
                        matched_free_code.add(sibling_block)
                clean_node = deepcopy(node)
                if isinstance(clean_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in clean_node.args.args:
                        arg.annotation = None
                    for arg in clean_node.args.kwonlyargs:
                        arg.annotation = None
                    if clean_node.args.vararg:
                        clean_node.args.vararg.annotation = None
                    if clean_node.args.kwarg:
                        clean_node.args.kwarg.annotation = None
                    clean_node.returns = None
                if clean_node.body and isinstance(clean_node.body[0], ast.Expr):
                    val = clean_node.body[0].value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        clean_node.body.pop(0)
                target_metadata = {
                    "name": node.name,
                    "signature": self._get_signature(node),
                    "code": ast.unparse(clean_node),
                    "docstring": ast.get_docstring(node),
                    "external_imports": sorted(list(set(matched_imports))),
                    "local_context_code": list(matched_free_code),
                    "used_names": sorted(list(extended_used_names)),
                }
                if isinstance(node, ast.ClassDef):
                    class_bases = [ast.unparse(b) for b in node.bases]
                    is_exception = (
                        "Error" in node.name
                        or "Exception" in node.name
                        or any(("Error" in b or "Exception" in b for b in class_bases))
                    )
                    target_metadata["bases"] = class_bases
                    if is_exception:
                        analysis["exceptions"].append(target_metadata)
                    else:
                        analysis["classes"].append(target_metadata)
                else:
                    analysis["functions"].append(target_metadata)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__all__" and isinstance(
                            node.value, (ast.List, ast.Tuple)
                        ):
                            analysis["dunder_all"] = [
                                ast.literal_eval(el) for el in node.value.elts
                            ]
                            analysis["flags"]["has_dunder_all"] = True
                        elif target.id.startswith("__") and target.id.endswith("__"):
                            continue
                        elif target.id.isupper():
                            analysis["constants"][target.id] = ast.unparse(node.value)
                        else:
                            analysis["free_floating_code"].append(ast.unparse(node))
            elif isinstance(node, ast.If) and self._is_main_boilerplate(node):
                continue
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, str
                ):
                    if not analysis["module_docstring"]:
                        analysis["module_docstring"] = node.value.value.strip()
                else:
                    analysis["free_floating_code"].append(ast.unparse(node))
            else:
                analysis["free_floating_code"].append(ast.unparse(node))
        analysis["flags"]["has_free_floating_code"] = (
            len(analysis["free_floating_code"]) > 0
        )
        analysis["flags"]["profile"] = self._determine_profile(analysis)
        return analysis

    def _get_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    ) -> str:
        decorator_list = [f"@{ast.unparse(d)}" for d in node.decorator_list]
        decorators = f"{' '.join(decorator_list)}\n" if decorator_list else ""
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            base_str = f"({', '.join(bases)})" if bases else ""
            return f"{decorators}class {node.name}{base_str}:"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = ast.unparse(node.args)
            return_annotation = ""
            if node.returns:
                return_annotation = f" -> {ast.unparse(node.returns)}"
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{decorators}{prefix} {node.name}({args}){return_annotation}:"
        return ""

    def _is_main_boilerplate(self, node: ast.If) -> bool:
        if not isinstance(node.test, ast.Compare):
            return False
        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Eq):
            return False
        elements = [self._get_node_value(node.test.left)]
        elements.extend((self._get_node_value(comp) for comp in node.test.comparators))
        return "__name__" in elements and "__main__" in elements

    def _get_node_value(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _determine_profile(self, analysis: Dict[str, Any]) -> str:
        has_funcs = len(analysis["functions"]) > 0
        has_classes = len(analysis["classes"]) > 0
        has_exceptions = len(analysis["exceptions"]) > 0
        has_constants = len(analysis["constants"]) > 0
        if has_constants and (not (has_funcs or has_classes or has_exceptions)):
            return "CONSTANT_REGISTRY"
        if (
            has_exceptions
            and (not has_classes)
            and (len(analysis["exceptions"]) >= len(analysis["functions"]))
        ):
            return "EXCEPTION_REGISTRY"
        if has_funcs and (not has_classes):
            return "FUNCTIONAL_UTILITY"
        if has_classes:
            return "COMPLEX_MODULE"
        return "STANDARD_MODULE"
