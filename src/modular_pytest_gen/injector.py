import sys
from typing import List

import libcst as cst


class AutodocInjector(cst.CSTTransformer):
    def __init__(self, target_path_str: str, new_docstring: str):

        self.target_path = target_path_str.split(".")
        self.new_docstring = new_docstring if new_docstring else ""
        self.current_path: List[str] = []

    def visit_ClassDef(self, node: cst.ClassDef):

        self.current_path.append(node.name.value)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:

        is_target = self.current_path == self.target_path
        self.current_path.pop()
        if is_target:
            return self._inject_docstring_into_body(updated_node)
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef):

        self.current_path.append(node.name.value)
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:

        is_target = self.current_path == self.target_path
        self.current_path.pop()
        if is_target:
            return self._inject_docstring_into_body(updated_node)
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:

        if len(self.target_path) == 1:
            return self._inject_constant_docstring(updated_node, self.target_path[0])
        return updated_node

    def _inject_docstring_into_body(self, node):

        if not self.new_docstring:
            return node
        docstring_expr = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=self.new_docstring))]
        )
        body_elements = list(node.body.body)
        if not body_elements:
            return node.with_deep_changes(
                node.body, body=[docstring_expr, cst.SimpleStatementLine([cst.Pass()])]
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
        return node.with_deep_changes(node.body, body=body_elements)

    def _inject_constant_docstring(
        self, node: cst.Module, target_name: str
    ) -> cst.Module:

        if not self.new_docstring:
            return node
        new_body = []
        docstring_expr = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=self.new_docstring))]
        )
        i = 0
        body_elements = list(node.body)
        while i < len(body_elements):
            stmt = body_elements[i]
            new_body.append(stmt)
            is_match = False
            if isinstance(stmt, cst.SimpleStatementLine):
                for expr in stmt.body:
                    if isinstance(expr, cst.Assign):
                        for target in expr.targets:
                            if hasattr(target, "target") and isinstance(
                                target.target, cst.Name
                            ):
                                if target.target.value == target_name:
                                    is_match = True
                                    break
            if is_match:
                if i + 1 < len(body_elements):
                    next_stmt = body_elements[i + 1]
                    if (
                        isinstance(next_stmt, cst.SimpleStatementLine)
                        and isinstance(next_stmt.body[0], cst.Expr)
                        and isinstance(next_stmt.body[0].value, cst.SimpleString)
                    ):
                        new_body.append(docstring_expr)
                        i += 2
                        continue
                new_body.append(docstring_expr)
            i += 1
        return node.with_changes(body=new_body)


def inject_autodoc(source_code: str, target_function: str, new_docstring: str) -> str:

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
        injector = AutodocInjector(target_function, new_docstring)
        modified_tree = tree.visit(injector)
        return modified_tree.code
    except Exception as e:
        print(
            f"\n[FATAL INJECTOR ERROR] Failed to parse signature for {target_function}",
            file=sys.stderr,
        )
        print("=============================", file=sys.stderr)
        raise e
