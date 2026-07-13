import ast
import sys
import textwrap
from typing import List

import libcst as cst


class AutodocInjector(cst.CSTTransformer):
    def __init__(
        self,
        target_function: str,
        new_docstring: str,
    ):
        self.target_function = target_function
        self.new_docstring = new_docstring if new_docstring else ""
        self.signature_node = None


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

def inject_autodoc(
    source_code: str,
    target_function: str,
    new_docstring: str,
) -> str:
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
    try:
        injector = AutodocInjector(
            target_function, new_docstring
        )
        modified_tree = tree.visit(injector)
        return modified_tree.code
    except Exception as e:
        print(
            f"\n[FATAL INJECTOR ERROR] Failed to parse signature for {target_function}",
            file=sys.stderr,
        )
        print("=============================", file=sys.stderr)
        raise e
    return tree.code
