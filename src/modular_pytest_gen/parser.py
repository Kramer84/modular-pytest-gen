import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Set


class ModuleParser:
    r"""
    Parse Python source code into structured metadata.

    The ModuleParser class analyzes Python source files to extract
    module-level components, including imports, constants, functions,
    classes, and exceptions. It provides detailed metadata about each
    component, including signatures, docstrings, and dependencies.

    Parameters
    ----------
    file_path : str | Path
        The path to the Python source file to be parsed.

    Attributes
    ----------
    file_path : Path
        The normalized path to the source file.
    source_code : str
        The raw content of the source file.
    tree : ast.AST
        The abstract syntax tree of the source code.

    Methods
    -------
    parse :
        Parse the source code and return structured metadata.
    _build_target_metadata :
        Build metadata for a specific target node.
    _get_signature :
        Get the signature of a function, method, or class.
    _is_main_boilerplate :
        Check if a node is a main boilerplate.
    _get_node_value :
        Get the value of a node.
    _determine_profile :
        Determine the profile of the module.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    SyntaxError
        If the source code contains syntax errors.
    """

    def __init__(self, file_path: str | Path):
        r"""
        Initialize a code parser with a file path.

        Creates a parser instance for the specified file, reads its
        contents, and constructs an Abstract Syntax Tree (AST)
        representation.

        Warnings
        --------
        Ensure the file exists and is readable to avoid runtime errors.

        See Also
        --------
        ast.parse :
            Standard library function used to generate the AST.

        Notes
        -----
        The parser handles both string paths and Path objects for file
        location specification.
        """

        self.file_path = Path(file_path)
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()
        self.tree = ast.parse(self.source_code)

    def parse(self) -> Dict[str, Any]:
        r"""
        Parse the AST tree into a structured metadata dictionary.

        This method processes the Abstract Syntax Tree (AST) of a Python
        module, extracting and organizing information about imports,
        constants, exceptions, classes, functions, and methods. It also
        identifies free-floating code and determines the module's profile.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the parsed metadata with the following
            keys:

            - `filename`: The name of the file being parsed.
            - `module_docstring`: The module-level docstring.
            - `dunder_all`: The contents of the `__all__` list if present.
            - `constants`: A dictionary of constants and their docstrings.
            - `exceptions`: A list of custom exception classes.
            - `classes`: A list of class definitions.
            - `functions`: A list of function definitions.
            - `methods`: A list of method definitions.
            - `free_floating_code`: A list of code blocks not associated
              with any specific construct.
            - `flags`: A dictionary of flags indicating the presence of
              certain constructs and the module's profile.

        Raises
        ------
        AttributeError
            If the AST tree is not properly initialized.

        Warnings
        --------
        This method assumes the AST tree is correctly parsed and may
        produce incorrect results if the tree is malformed.
        """

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
        r"""
        Constructs metadata for a target AST node.

        This method aggregates structural and contextual information about
        a given AST node, including its dependencies, imports, and local
        context. It is used internally by the AST scanner to provide
        comprehensive metadata for code analysis and documentation
        generation.

        Parameters
        ----------
        node : ast.AST
            The AST node to analyze.
        import_registry : Dict[str, Dict[str, Any]]
            A registry of imported modules and their metadata.
        free_floating_registry : Dict[str, str]
            A registry of free-floating code blocks and their associated
            names.
        internal_sibling_registry : Dict[str, str]
            A registry of internal sibling code blocks and their associated
            names.
        parent_class_name : Optional[str], optional
            The name of the parent class if the node is a method.
        class_methods : Optional[Dict[str, str]], optional
            A dictionary of class methods and their code.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the following keys:

            - `name`: The qualified name of the node.
            - `signature`: The signature of the node.
            - `code`: The cleaned-up code of the node.
            - `docstring`: The docstring of the node.
            - `external_imports`: A list of external imports used by the
              node.
            - `local_context_code`: A list of local context code blocks
              used by the node.
            - `used_names`: A list of names used by the node.

        See Also
        --------
        ast.AST :
            The base class for all AST nodes.
        ast.walk :
            A function to recursively walk an AST node.
        ast.unparse :
            A function to convert an AST node back to source code.
        ast.get_docstring :
            A function to extract the docstring from an AST node.
        """

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
        r"""
        Extracts the signature string from an AST node.

        This method is used internally to generate the signature string for
        a given AST node, which can be a function, async function, or class
        definition. The signature string includes decorators, the node
        name, base classes for classes, arguments for functions, and return
        annotations if present.

        Parameters
        ----------
        node : ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            The AST node from which to extract the signature string.

        Returns
        -------
        str
            The signature string of the AST node.

            For a class, the string includes the class name and base
            classes.

            For a function or async function, the string includes the
            function name, arguments, and return annotation if present.

        Raises
        ------
        TypeError
            If the node is not an instance of ast.FunctionDef,
            ast.AsyncFunctionDef, or ast.ClassDef.
        """

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
        r"""
        Check if ast node is main guard block.

        This method checks if the provided AST node is a conditional
        statement that evaluates whether the script is being run directly
        or imported. It verifies the structure of the node to ensure it
        matches the boilerplate pattern.

        Parameters
        ----------
        node : ast.If
            The AST node to be evaluated.

        Returns
        -------
        bool
            Returns `True` if the node matches the boilerplate pattern,
            otherwise `False`.

        Raises
        ------
        TypeError
            If the provided node is not an instance of `ast.If`.
        """

        if not isinstance(node.test, ast.Compare):
            return False
        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Eq):
            return False
        elements = [self._get_node_value(node.test.left)]
        elements.extend((self._get_node_value(comp) for comp in node.test.comparators))
        return "__name__" in elements and "__main__" in elements

    def _get_node_value(self, node: ast.AST) -> Optional[str]:
        r"""
        Retrieve the string value from an AST node.

        This method extracts the string representation of a node's value if
        it is either a variable name or a constant string.

        Parameters
        ----------
        node : ast.AST
            The AST node to extract the value from.

        Returns
        -------
        Optional[str]
            The string value of the node if it is a variable name or
            constant string, otherwise `None`.

        Raises
        ------
        TypeError
            If the node type is not supported for value extraction.
        """

        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _determine_profile(self, analysis: Dict[str, Any]) -> str:
        r"""
        Determine the module profile based on AST analysis results.

        This method evaluates the AST analysis results to classify the
        module into one of several predefined profiles. The classification
        is based on the presence and quantity of functions, classes,
        exceptions, and constants.

        Parameters
        ----------
        analysis : Dict[str, Any]
            A dictionary containing the AST analysis results with keys for
            functions, classes, exceptions, and constants.

        Returns
        -------
        str
            The determined module profile, which can be one of the
            following:

            - `CONSTANT_REGISTRY`: If the module contains only constants.
            - `EXCEPTION_REGISTRY`: If the module contains more exceptions
              than functions and no classes.
            - `FUNCTIONAL_UTILITY`: If the module contains functions but no
              classes.
            - `COMPLEX_MODULE`: If the module contains classes.
            - `STANDARD_MODULE`: If none of the above conditions are met.

        Raises
        ------
        KeyError
            If the `analysis` dictionary is missing any of the required
            keys (`functions`, `classes`, `exceptions`, `constants`).
        """

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
