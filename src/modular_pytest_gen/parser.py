import ast
from pathlib import Path
from typing import Any, Dict, Optional


class ModuleParser:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()
        self.tree = ast.parse(self.source_code)

    def parse(self) -> Dict[str, Any]:
        """Parses the python file and returns a structured analysis profile."""
        analysis = {
            "filename": self.file_path.name,
            "module_docstring": ast.get_docstring(self.tree),
            "dunder_all": None,
            "imports": [],
            "constants": {},
            "exceptions": [],
            "classes": [],
            "functions": [],
            "free_floating_code": [],
            "flags": {
                "has_dunder_all": False,
                "has_free_floating_code": False,
                "profile": "UNKNOWN"
            }
        }

        for node in self.tree.body:
            # 1. Track Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                analysis["imports"].append(ast.unparse(node))

            # 2. Track Top-Level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                analysis["functions"].append({
                    "name": node.name,
                    "signature": self._get_function_signature(node),
                    "code": ast.unparse(node),
                    "docstring": ast.get_docstring(node)
                })

            # 3. Track Classes (Differentiating Exceptions vs Normal Classes)
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "bases": [ast.unparse(b) for b in node.bases],
                    "code": ast.unparse(node),
                    "docstring": ast.get_docstring(node)
                }
                
                # Broaden exception detection: check class name and bases for "Error" or "Exception"
                is_exception = (
                    "Error" in class_info["name"] or "Exception" in class_info["name"] or
                    any("Error" in b or "Exception" in b for b in class_info["bases"])
                )
                
                if is_exception:
                    analysis["exceptions"].append(class_info)
                else:
                    analysis["classes"].append(class_info)

            # 4. Track Top-Level Assignments (Constants, __all__, and dunder metadata)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                            analysis["dunder_all"] = [ast.literal_eval(el) for el in node.value.elts]
                            analysis["flags"]["has_dunder_all"] = True
                        elif target.id.startswith("__") and target.id.endswith("__"):
                            # Silently ignore standard module metadata (e.g., __author__)
                            continue
                        elif target.id.isupper():
                            analysis["constants"][target.id] = ast.unparse(node.value)
                        else:
                            analysis["free_floating_code"].append(ast.unparse(node))

            # 5. Catch boilerplate runner 'if __name__ == "__main__":' flexibly
            elif isinstance(node, ast.If) and self._is_main_boilerplate(node):
                continue

            # 6. Fallback and Context extraction for ast.Expr 
            elif isinstance(node, ast.Expr):
                # If it's a floating string, it's a docstring/comment, not executable code
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if not analysis["module_docstring"]:
                        analysis["module_docstring"] = node.value.value.strip()
                else:
                    analysis["free_floating_code"].append(ast.unparse(node))
            
            # Catch true free-floating executable statements (loops, etc.)
            else:
                analysis["free_floating_code"].append(ast.unparse(node))

        # Evaluate Flags and Profile
        analysis["flags"]["has_free_floating_code"] = len(analysis["free_floating_code"]) > 0
        analysis["flags"]["profile"] = self._determine_profile(analysis)

        return analysis

    def _get_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Helper to extract the definition line of a function, preserving type hints."""
        decorator_list = [f"@{ast.unparse(d)}" for d in node.decorator_list]
        args = ast.unparse(node.args)
        
        return_annotation = ""
        if node.returns:
            return_annotation = f" -> {ast.unparse(node.returns)}"
            
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        decorators = f"{' '.join(decorator_list)}\n" if decorator_list else ""
        
        return f"{decorators}{prefix} {node.name}({args}){return_annotation}:"

    def _is_main_boilerplate(self, node: ast.If) -> bool:
        """Evaluates if an If node is a main execution block regardless of syntax order."""
        if not isinstance(node.test, ast.Compare):
            return False

        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Eq):
            return False

        elements = [self._get_node_value(node.test.left)]
        elements.extend(self._get_node_value(comp) for comp in node.test.comparators)

        return "__name__" in elements and "__main__" in elements

    def _get_node_value(self, node: ast.AST) -> Optional[str]:
        """Resolves specific ast literal types to their underlying string name or value."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _determine_profile(self, analysis: Dict[str, Any]) -> str:
        """Heuristic logic to classify the script style."""
        has_funcs = len(analysis["functions"]) > 0
        has_classes = len(analysis["classes"]) > 0
        has_exceptions = len(analysis["exceptions"]) > 0
        has_constants = len(analysis["constants"]) > 0

        if has_constants and not (has_funcs or has_classes or has_exceptions):
            return "CONSTANT_REGISTRY"
            
        # Exception registry heuristic: more exceptions than functions, no standard classes
        if has_exceptions and not has_classes and len(analysis["exceptions"]) >= len(analysis["functions"]):
            return "EXCEPTION_REGISTRY"
            
        if has_funcs and not has_classes:
            return "FUNCTIONAL_UTILITY"
            
        if has_classes:
            return "COMPLEX_MODULE"
            
        return "STANDARD_MODULE"