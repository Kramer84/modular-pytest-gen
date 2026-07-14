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
        analysis: Dict[str, Any] = {
            "filename": self.file_path.name,
            "module_docstring": ast.get_docstring(self.tree),
            "dunder_all": None,
            "constants": {},
            "exceptions": [],
            "classes": [],
            "functions": [],
            "methods": [],
            "free_floating_code": [],
            "flags": {
                "has_dunder_all": False,
                "has_free_floating_code": False,
                "profile": "UNKNOWN",
            },
        }
        for i, node in enumerate(self.tree.body):
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
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                internal_sibling_registry[node.name] = ast.unparse(node)
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
                            docstring = None
                            if i + 1 < len(self.tree.body):
                                next_node = self.tree.body[i + 1]
                                if (
                                    isinstance(next_node, ast.Expr)
                                    and isinstance(next_node.value, ast.Constant)
                                    and isinstance(next_node.value.value, str)
                                ):
                                    docstring = next_node.value.value.strip()
                            analysis["constants"][target.id] = {
                                "value": ast.unparse(node.value),
                                "docstring": docstring,
                            }
                        else:
                            free_floating_registry[target.id] = ast.unparse(node)
            elif isinstance(node, ast.If) and self._is_main_boilerplate(node):
                continue
            elif isinstance(node, ast.Expr):
                if (
                    i == 0
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    pass
                else:
                    analysis["free_floating_code"].append(ast.unparse(node))
            else:
                analysis["free_floating_code"].append(ast.unparse(node))
        analysis["free_floating_code"].extend(
            list(set(free_floating_registry.values()))
        )
        analysis["flags"]["has_free_floating_code"] = (
            len(analysis["free_floating_code"]) > 0
        )
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                analysis["functions"].append(
                    self._build_target_metadata(
                        node,
                        import_registry,
                        free_floating_registry,
                        internal_sibling_registry,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                class_meta = self._build_target_metadata(
                    node,
                    import_registry,
                    free_floating_registry,
                    internal_sibling_registry,
                )
                class_bases = [ast.unparse(b) for b in node.bases]
                is_exception = (
                    "Error" in node.name
                    or "Exception" in node.name
                    or any(("Error" in b or "Exception" in b for b in class_bases))
                )
                class_meta["bases"] = class_bases
                if is_exception:
                    analysis["exceptions"].append(class_meta)
                else:
                    analysis["classes"].append(class_meta)
                class_docstring = ast.get_docstring(node)
                class_methods = {
                    child.name: ast.unparse(child)
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_meta = self._build_target_metadata(
                            node=child,
                            import_registry=import_registry,
                            free_floating_registry=free_floating_registry,
                            internal_sibling_registry=internal_sibling_registry,
                            parent_class_name=node.name,
                            class_methods=class_methods,
                        )
                        if class_docstring:
                            method_meta["local_context_code"].insert(
                                0, f'"""Parent Class Docstring:\n{class_docstring}\n"""'
                            )
                        if "__init__" in class_methods and child.name != "__init__":
                            method_meta["local_context_code"].insert(
                                1,
                                f"# Parent Initialization:\n{class_methods['__init__']}",
                            )
                        analysis["methods"].append(method_meta)
        analysis["flags"]["profile"] = self._determine_profile(analysis)
        return analysis

    def _build_target_metadata(
        self,
        node,
        import_registry,
        free_floating_registry,
        internal_sibling_registry,
        parent_class_name=None,
        class_methods=None,
    ) -> Dict[str, Any]:

        immediate_names: Set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                immediate_names.add(child.id)
            elif isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == "self":
                    immediate_names.add(f"self.{child.attr}")
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
            if current_name in internal_sibling_registry and current_name != (
                parent_class_name or node.name
            ):
                sibling_code = internal_sibling_registry[current_name]
                sibling_block = (
                    f"# Sibling dependency defined in this module:\n{sibling_code}"
                )
                matched_free_code.add(sibling_block)
                try:
                    for sub_child in ast.walk(ast.parse(sibling_code)):
                        if isinstance(sub_child, ast.Name):
                            extended_used_names.add(sub_child.id)
                            names_to_check.append(sub_child.id)
                except Exception:
                    pass
        if class_methods:
            for name in extended_used_names:
                if name.startswith("self."):
                    method_name = name.split(".")[1]
                    if method_name in class_methods and method_name != node.name:
                        matched_free_code.add(
                            f"# Internal sibling method called:\n{class_methods[method_name]}"
                        )
        matched_imports = []
        for name in extended_used_names:
            if name in import_registry:
                meta = import_registry[name]
                if meta["type"] == "absolute":
                    stmt = f"import {meta['module']}" + (
                        f" as {meta['alias']}" if meta["alias"] else ""
                    )
                    matched_imports.append(stmt)
                elif meta["type"] == "from":
                    stmt = (
                        f"from {'.' * meta['level']}{meta['module']} import {meta['name']}"
                        + (f" as {meta['alias']}" if meta["alias"] else "")
                    )
                    matched_imports.append(stmt)
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
        qual_name = (
            f"{parent_class_name}.{node.name}" if parent_class_name else node.name
        )
        return {
            "name": qual_name,
            "signature": self._get_signature(node),
            "code": ast.unparse(clean_node),
            "docstring": ast.get_docstring(node),
            "external_imports": sorted(list(set(matched_imports))),
            "local_context_code": list(matched_free_code),
            "used_names": sorted(list(extended_used_names)),
        }

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
