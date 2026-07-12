import libcst as cst
import textwrap
from typing import List

def format_docstring(raw_doc: str, base_indent: int, max_line_length: int = 78) -> str:
    """
    Dedents the raw docstring, hard-wraps text strictly to max_line_length 
    while respecting NumPy blocks, and re-indents to the target scope.
    """
    # 1. Strip hallucinated global whitespace, preserving relative parameter indents
    raw_doc = textwrap.dedent(raw_doc).strip()
    lines = raw_doc.splitlines()
    
    formatted_lines = []
    in_code_block = False
    
    # Calculate available characters (e.g., 78 max - 8 indent = 70 text chars)
    text_width = max_line_length - base_indent
    
    for line in lines:
        stripped = line.strip()
        
        # Toggle block states to avoid wrapping code or math equations
        if stripped.startswith("```") or stripped.startswith(".. code") or stripped.startswith(".. math"):
            in_code_block = not in_code_block
            
        # Skip wrapping for blocks, doctests, headers (---), or empty lines
        if in_code_block or stripped.startswith(">>>") or stripped.startswith("...") or set(stripped) == {"-"} or not stripped:
            formatted_lines.append(line)
            continue
            
        internal_indent = len(line) - len(line.lstrip())
        
        if len(line) > text_width:
            wrapper = textwrap.TextWrapper(
                width=text_width,
                initial_indent=" " * internal_indent,
                subsequent_indent=" " * internal_indent,
                break_long_words=False,
                break_on_hyphens=False
            )
            wrapped_text = wrapper.fill(line.lstrip())
            formatted_lines.extend(wrapped_text.splitlines())
        else:
            formatted_lines.append(line)
            
    # 2. Re-apply the exact base_indent for the target function's scope
    base_space = " " * base_indent
    final_lines = [(base_space + l if l else "") for l in formatted_lines]
    
    # 3. Wrap in a raw multi-line string to protect LaTeX (\frac, \sigma)
    return f'r"""\n{"\n".join(final_lines)}\n{base_space}"""'

class AutodocInjector(cst.CSTTransformer):
    """
    Safely injects docstrings, updates function signatures, and adds required 
    imports using a Concrete Syntax Tree to preserve all surrounding formatting.
    """
    def __init__(self, target_function: str, new_docstring: str, updated_signature: str, new_imports: List[str]):
        self.target_function = target_function
        self.new_docstring = f'"""\n{new_docstring.strip()}\n"""' if new_docstring else ""
        self.new_imports = new_imports
        self.signature_node = None
        
        if updated_signature:
            try:
                dummy_code = f"{updated_signature.strip()}\n    pass"
                dummy_module = cst.parse_module(dummy_code)
                self.signature_node = dummy_module.body[0]
            except Exception:
                pass

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
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
            if isinstance(node, cst.SimpleStatementLine) and isinstance(node.body[0], (cst.Import, cst.ImportFrom))
        ]
        
        unique_import_nodes = []
        for node, imp_str in zip(import_nodes, self.new_imports):
            if imp_str.strip() not in existing_imports:
                unique_import_nodes.append(node)

        if not unique_import_nodes:
            return updated_node

        insert_index = 0
        for i, node in enumerate(updated_node.body):
            if isinstance(node, cst.SimpleStatementLine) and isinstance(node.body[0], (cst.Import, cst.ImportFrom)):
                insert_index = i + 1

        new_body = list(updated_node.body)
        for imp_node in reversed(unique_import_nodes):
            new_body.insert(insert_index, imp_node)

        return updated_node.with_changes(body=new_body)

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        if original_node.name.value != self.target_function:
            return updated_node

        modified_node = updated_node
        if self.signature_node and isinstance(self.signature_node, cst.FunctionDef):
            modified_node = modified_node.with_changes(
                params=self.signature_node.params,
                returns=self.signature_node.returns
            )

        if self.new_docstring:
            docstring_expr = cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.SimpleString(value=self.new_docstring))]
            )
            body_elements = list(modified_node.body.body)
            
            if not body_elements:
                return modified_node.with_deep_changes(
                    modified_node.body, body=[docstring_expr, cst.SimpleStatementLine([cst.Pass()])]
                )

            first_stmt = body_elements[0]
            if isinstance(first_stmt, cst.SimpleStatementLine) and isinstance(first_stmt.body[0], cst.Expr) and isinstance(first_stmt.body[0].value, cst.SimpleString):
                body_elements[0] = docstring_expr
            else:
                body_elements.insert(0, docstring_expr)

            modified_node = modified_node.with_deep_changes(modified_node.body, body=body_elements)

        return modified_node

def inject_autodoc(source_code: str, target_function: str, new_docstring: str, updated_signature: str, new_imports: List[str]) -> str:
    """Parses the source, applies the injection transformer, and returns the modified code."""
    tree = cst.parse_module(source_code)
    injector = AutodocInjector(target_function, new_docstring, updated_signature, new_imports)
    modified_tree = tree.visit(injector)
    return modified_tree.code