import ast
from pathlib import Path
from typing import Set

class TestMerger:
    """
    Scans the temporary testing registry, combines isolated unit tests 
    belonging to the same target source script, and builds a clean test file.
    """
    def __init__(self, tmp_dir: str | Path = "_tests.tmp"):
        self.tmp_dir = Path(tmp_dir)

    def merge_all(self, final_test_root: str | Path):
        final_root = Path(final_test_root)
        if not self.tmp_dir.exists():
            print(f"[MERGE] No temporary directory found at {self.tmp_dir}. Skipping merge.")
            return

        # Find all target module subdirectories within the temporary folder
        for module_dir in self.tmp_dir.iterdir():
            if not module_dir.is_dir():
                continue

            # Determine the target consolidated file path
            relative_target = module_dir.relative_to(self.tmp_dir)
            consolidated_test_file = final_root / relative_target.with_name(f"test_{relative_target.name}.py")
            consolidated_test_file.parent.mkdir(parents=True, exist_ok=True)

            print(f"[MERGE] Consolidating tests for module: {relative_target.name}")

            all_imports: Set[str] = set()
            all_fixtures: list[str] = []
            all_cases: list[str] = []

            # Read every temporary function script inside this module folder
            for test_script in module_dir.glob("*.py"):
                try:
                    content = test_script.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                    
                    # Group code structures semantically using AST nodes
                    for node in tree.body:
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            all_imports.add(ast.unparse(node))
                        elif isinstance(node, ast.FunctionDef):
                            node_code = ast.unparse(node)
                            if node.name.startswith("test_"):
                                all_cases.append(node_code)
                            else:
                                all_fixtures.append(node_code)
                except Exception as e:
                    print(f"  [WARN] Failed to parse temporary file {test_script.name}: {e}")

            if not all_cases:
                continue

            # Compile into a single structured output script
            merged_content = [
                '# Generated Modular Pytest Suite',
                'import pytest',
                "\n".join(sorted(list(all_imports)))
            ]
            
            if all_fixtures:
                merged_content.append("\n\n".join(all_fixtures))
                
            merged_content.append("\n\n".join(all_cases))

            consolidated_test_file.write_text("\n\n".join(merged_content) + "\n", encoding="utf-8")
            print(f"  [SUCCESS] Created consolidated file -> {consolidated_test_file}")