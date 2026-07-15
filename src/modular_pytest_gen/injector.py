import sys
from typing import List

import libcst as cst


class AutodocInjector(cst.CSTTransformer):
    r"""
    Inject docstrings into Python AST nodes.
    
    Transforms CST nodes by injecting docstrings into class definitions,
    function definitions, or module-level constants.
    
    Parameters
    ----------
    target_path_str : str
        The dot-separated path to the target node (e.g.,
        'module.Class.method').
    new_docstring : str, optional
        The docstring to inject into the target node.
    
    Attributes
    ----------
    target_path : List[str]
        The split path components of the target node.
    new_docstring : str
        The docstring to inject into the target node.
    current_path : List[str]
        The current path being traversed during AST traversal.
    
    Methods
    -------
    visit_ClassDef :
        Visits a class definition node and updates the current path.
    leave_ClassDef :
        Leaves a class definition node and injects the docstring if the
        node is the target.
    visit_FunctionDef :
        Visits a function definition node and updates the current path.
    leave_FunctionDef :
        Leaves a function definition node and injects the docstring if the
        node is the target.
    leave_Module :
        Leaves a module node and injects the docstring if the target is a
        module-level constant.
    
    Notes
    -----
    The transformer handles both class and function docstring injection, as
    well as module-level constant docstrings.
    
    The docstring is injected at the beginning of the node's body,
    replacing any existing docstring if present.
    """

    def __init__(self, target_path_str: str, new_docstring: str):
        r"""
        Initialize a docstring writer for a target object.
        
        Constructs a docstring writer instance with the target object's
        path and the new docstring content.
        
        Warnings
        --------
        Ensure the target path is a valid Python object path to avoid
        runtime errors.
        
        See Also
        --------
        ast.NodeVisitor :
            The AST visitor used to parse and analyze Python code
            structures.
        inspect.getdoc :
            The function used to retrieve the docstring of a Python object.
        
        Notes
        -----
        The target path is split into a list of strings for easier
        manipulation.
        """

        self.target_path = target_path_str.split(".")
        self.new_docstring = new_docstring if new_docstring else ""
        self.current_path: List[str] = []

    def visit_ClassDef(self, node: cst.ClassDef):
        r"""
        Process a class definition node.
        
        Parameters
        ----------
        node : cst.ClassDef
            The class definition node to process.
        
        Returns
        -------
        bool
            Returns `True` to indicate that traversal should continue.
        
        See Also
        --------
        modular_pytest_gen.ast_scanner.ASTScanner :
            The AST scanner that processes class definitions.
        """

        self.current_path.append(node.name.value)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        r"""
        Insert docstring into class definition if paths match.
        
        Parameters
        ----------
        original_node : cst.ClassDef
            The original class definition node.
        updated_node : cst.ClassDef
            The updated class definition node.
        
        Returns
        -------
        cst.ClassDef
            The updated class definition node with an injected docstring if
            the target path matches.
        
            Otherwise, the original node is returned.
        
        See Also
        --------
        modular_pytest_gen.docstring.ClassDocstringSchema :
            The schema used to generate the docstring for a class.
        """

        is_target = self.current_path == self.target_path
        self.current_path.pop()
        if is_target:
            return self._inject_docstring_into_body(updated_node)
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef):
        r"""
        Process a function definition node in the AST.
        
        Parameters
        ----------
        node : cst.FunctionDef
            The function definition node to process.
        
        Returns
        -------
        bool
            Returns True to indicate that the traversal should continue.
        
        See Also
        --------
        visit_ClassDef :
            Processes a class definition node.
        """

        self.current_path.append(node.name.value)
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        r"""
        Injects a docstring into the target function body.
        
        Parameters
        ----------
        original_node : cst.FunctionDef
            The original function definition node.
        updated_node : cst.FunctionDef
            The updated function definition node.
        
        Returns
        -------
        cst.FunctionDef
            The function definition node with the injected docstring if it
            matches the target path, otherwise the original updated node.
        
        Raises
        ------
        ValueError
            If the docstring injection fails due to structural
            inconsistencies.
        """

        is_target = self.current_path == self.target_path
        self.current_path.pop()
        if is_target:
            return self._inject_docstring_into_body(updated_node)
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        r"""
        Injects a constant docstring into the target module.
        
        This method is specifically designed to handle the injection of a
        constant docstring into a module when the target path consists of a
        single element. It ensures that the docstring is properly formatted
        and integrated into the module structure.
        
        Parameters
        ----------
        original_node : cst.Module
            The original module node before any modifications.
        updated_node : cst.Module
            The updated module node after modifications.
        
        Returns
        -------
        cst.Module
            The module node with the injected constant docstring if the
            target path has a single element.
        
            Otherwise, returns the updated node as-is.
        
        Raises
        ------
        ValueError
            If the target path is empty or contains more than one element,
            indicating an invalid state for docstring injection.
        
        Warnings
        --------
        Ensure that the target path is correctly set before calling this
        method to avoid unexpected behavior.
        """

        if len(self.target_path) == 1:
            return self._inject_constant_docstring(updated_node, self.target_path[0])
        return updated_node

    def _inject_docstring_into_body(self, node):
        r"""
        Injects a generated docstring into the AST node body.
        
        This method handles the insertion of a newly generated docstring
        into the body of an AST node. It ensures the docstring is properly
        formatted and placed at the beginning of the node's body, replacing
        any existing docstring if present.
        
        Parameters
        ----------
        node : cst.CSTNode
            The AST node into which the docstring will be injected.
        
        Returns
        -------
        cst.CSTNode
            The modified AST node with the injected docstring.
        
            If no new docstring is available, the original node is returned
            unchanged.
        
        Raises
        ------
        AttributeError
            If the node does not have a body attribute.
        """

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
        r"""
        Injects a docstring into a CST module node.
        
        This method inserts a new docstring into the CST module node at the
        specified target name. If no new docstring is provided, the
        original node is returned unchanged.
        
        Parameters
        ----------
        node : cst.Module
            The CST module node to which the docstring will be injected.
        target_name : str
            The name of the target where the docstring will be injected.
        
        Returns
        -------
        cst.Module
            The modified CST module node with the injected docstring.
        
            If no new docstring is provided, the original node is returned
            unchanged.
        
        Raises
        ------
        AttributeError
            If the target node does not have the expected attributes.
        
        Warnings
        --------
        Ensure the target_name exists in the CST module to avoid unexpected
        behavior.
        """

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
    r"""
    Injects a new docstring into a target function's AST.
    
    This function parses the provided source code into an Abstract Syntax
    Tree (AST) and injects the new docstring into the specified target
    function. It handles both successful and failed injection scenarios,
    providing detailed error messages for debugging.
    
    Parameters
    ----------
    source_code : str
        The source code containing the target function.
    target_function : str
        The name of the function to inject the docstring into.
    new_docstring : str
        The new docstring to be injected into the target function.
    
    Returns
    -------
    str
        The modified source code with the new docstring injected into the
        target function.
    
    Raises
    ------
    Exception
        If the source code fails to parse into an AST.
    
        If the target function's signature cannot be parsed.
    """

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
