import ast
import sys
from typing import List

import libcst as cst


class AutodocInjector(cst.CSTTransformer):
    def __init__(
        self,
        target_function: str,
        new_docstring: str,
        updated_signature: str,
        new_imports: List[str],
    ):
        self.target_function = target_function
        self.new_docstring = new_docstring if new_docstring else ""
        self.new_imports = new_imports
        self.signature_node = None
        if updated_signature:
            try:
                dummy_code = f"{updated_signature.strip()}\n    pass"
                dummy_module = cst.parse_module(dummy_code)
                self.signature_node = dummy_module.body[0]
            except Exception:
                pass

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if not self.new_imports:
            return updated_node
        import_nodes = []
        for imp in self.new_imports:
            try:
                import_nodes.append(cst.parse_statement(imp.strip()))
            except Exception:
                continue
        existing_imports = [
            cst.Module([]).code_for_node(node).strip()
            for node in original_node.body
            if isinstance(node, cst.SimpleStatementLine)
            and isinstance(node.body[0], (cst.Import, cst.ImportFrom))
        ]
        unique_import_nodes = []
        for node, imp_str in zip(import_nodes, self.new_imports):
            if imp_str.strip() not in existing_imports:
                unique_import_nodes.append(node)
        if not unique_import_nodes:
            return updated_node
        insert_index = 0
        for i, node in enumerate(updated_node.body):
            if isinstance(node, cst.SimpleStatementLine) and isinstance(
                node.body[0], (cst.Import, cst.ImportFrom)
            ):
                insert_index = i + 1
        new_body = list(updated_node.body)
        for imp_node in reversed(unique_import_nodes):
            new_body.insert(insert_index, imp_node)
        return updated_node.with_changes(body=new_body)

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value != self.target_function:
            return updated_node
        modified_node = updated_node
        if self.signature_node and isinstance(self.signature_node, cst.FunctionDef):
            modified_node = modified_node.with_changes(
                params=self.signature_node.params, returns=self.signature_node.returns
            )
        if self.new_docstring:
            docstring_expr = cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.SimpleString(value=self.new_docstring))]
            )
            body_elements = list(modified_node.body.body)
            if not body_elements:
                return modified_node.with_deep_changes(
                    modified_node.body,
                    body=[docstring_expr, cst.SimpleStatementLine([cst.Pass()])],
                )
            first_stmt = body_elements[0]
            if (
                isinstance(first_stmt, cst.SimpleStatementLine)
                and isinstance(first_stmt.body[0], cst.Expr)
                and isinstance(first_stmt.body[0].value, cst.SimpleString)
            ):
                body_elements[0] = docstring_expr
            else:
                body_elements.insert(0, docstring_expr)
            modified_node = modified_node.with_deep_changes(
                modified_node.body, body=body_elements
            )
        return modified_node


def sanitize_imports(imports: list[str]) -> list[str]:
    r"""
    Sanitize import statements by removing forbidden beartype aliases.
    
    This function processes a list of import statements, parsing and
    validating each one to ensure it does not contain forbidden beartype
    aliases. It returns a list of sanitized import statements that are safe
    to use in the project.
    
    Parameters
    ----------
    imports : list[str]
        A list of import statements to be sanitized.
    
    Returns
    -------
    list[str]
        A list of sanitized import statements that do not contain forbidden
        beartype aliases.
    """
    clean_imports = []
    forbidden_beartype = {
        "dict",
        "list",
        "tuple",
        "set",
        "str",
        "int",
        "float",
        "bool",
        "NDArray",
    }
    for imp_str in imports:
        try:
            tree = ast.parse(imp_str)
            for node in tree.body:
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "beartype.typing"
                ):
                    valid_aliases = [
                        alias
                        for alias in node.names
                        if alias.name not in forbidden_beartype
                    ]
                    if valid_aliases:
                        new_node = ast.ImportFrom(
                            module=node.module, names=valid_aliases, level=node.level
                        )
                        clean_imports.append(ast.unparse(new_node))
                else:
                    clean_imports.append(imp_str)
        except Exception:
            pass
    return clean_imports


def inject_imports_safely(source_code: str, new_imports: list[str]) -> str:
    r"""
    Safely inject new import statements into Python source code.
    
    This function inserts new import statements into the source code while
    ensuring no duplicate imports are added. It handles various edge cases
    such as existing imports, docstrings, and syntax errors.
    
    Parameters
    ----------
    source_code : str
        The original Python source code as a string.
    new_imports : List[str]
        A list of new import statements to be added to the source code.
    
    Returns
    -------
    str
        The modified source code with the new imports inserted.
    
        If the source code contains syntax errors or no new imports are
        added, the original source code is returned unchanged.
    
    See Also
    --------
    modular_pytest_gen.sanitize_imports :
        Sanitizes import statements to ensure they do not contain forbidden
        beartype aliases.
    """
    new_imports = sanitize_imports(new_imports)
    if not new_imports:
        return source_code
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return source_code
    insert_line_idx = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            insert_line_idx = node.end_lineno
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            insert_line_idx = node.end_lineno
        else:
            break
    lines = source_code.splitlines()
    source_text = "\n".join(lines)
    unique_new_imports = [imp for imp in new_imports if imp not in source_text]
    if not unique_new_imports:
        return source_code
    lines[insert_line_idx:insert_line_idx] = unique_new_imports
    return "\n".join(lines) + "\n"


def inject_autodoc(
    source_code: str, target_function: str, new_docstring: str, updated_signature: str, new_imports: list[str]) -> str:
    r"""
    Injects a new docstring and signature into Python source code.
    
    This function safely injects new documentation and type hints into
    Python source code while maintaining code integrity. It handles import
    injection, syntax validation, and docstring insertion.
    
    Parameters
    ----------
    source_code : str
        The original Python source code as a string.
    target_function : str
        The name of the function to which the new docstring and signature
        will be injected.
    new_docstring : str
        The new docstring to be injected into the target function.
    updated_signature : str
        The updated function signature with type hints.
    new_imports : list[str]
        A list of new import statements to be added to the source code.
    
    Returns
    -------
    str
        The modified source code with the new docstring and signature
        injected.
    
        If the source code contains syntax errors or no new imports are
        added, the original source code is returned unchanged.
    
    See Also
    --------
    modular_pytest_gen.inject_imports_safely :
        Safely inject new import statements into Python source code.
    modular_pytest_gen.sanitize_imports :
        Sanitize import statements by removing forbidden beartype aliases.
    """
    if new_imports:
        try:
            source_code = inject_imports_safely(source_code, new_imports)
        except Exception as e:
            print(
                f"\n[FATAL INJECTOR ERROR] Failed to inject imports for {target_function}",
                file=sys.stderr,
            )
            print("=== PROBLEMATIC NEW IMPORTS ===", file=sys.stderr)
            print("\n".join(new_imports), file=sys.stderr)
            print("=============================", file=sys.stderr)
            raise e
    try:
        tree = cst.parse_module(source_code)
    except Exception as e:
        print(
            f"\n[FATAL INJECTOR ERROR] Failed to parse AST for {target_function}",
            file=sys.stderr,
        )
        print("=== PROBLEMATIC SOURCE CODE ===", file=sys.stderr)
        print(source_code, file=sys.stderr)
        print("===============================", file=sys.stderr)
        raise e
    if updated_signature:
        try:
            injector = AutodocInjector(
                target_function, new_docstring, updated_signature, new_imports
            )
            modified_tree = tree.visit(injector)
            return modified_tree.code
        except Exception as e:
            print(
                f"\n[FATAL INJECTOR ERROR] Failed to parse signature for {target_function}",
                file=sys.stderr,
            )
            print("=== PROBLEMATIC SIGNATURE ===", file=sys.stderr)
            print(repr(updated_signature), file=sys.stderr)
            print("=============================", file=sys.stderr)
            raise e
    return tree.code
