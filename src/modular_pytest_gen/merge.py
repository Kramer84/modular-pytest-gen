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
            print(
                f"[MERGE] No temporary directory found at {self.tmp_dir}. Skipping merge."
            )
            return
        for module_dir in self.tmp_dir.iterdir():
            if not module_dir.is_dir():
                continue
            relative_target = module_dir.relative_to(self.tmp_dir)
            consolidated_test_file = final_root / relative_target.with_name(
                f"test_{relative_target.name}.py"
            )
            all_imports: Set[str] = set()
            all_fixtures: list[str] = []
            all_cases: list[str] = []
            found_verified_tests = False
            for test_script in module_dir.rglob("*_verified.py"):
                found_verified_tests = True
                try:
                    content = test_script.read_text(encoding="utf-8")
                    tree = ast.parse(content)
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
                    print(
                        f"  [WARN] Failed to parse verified file {test_script.name}: {e}"
                    )
            if not found_verified_tests or not all_cases:
                continue
            consolidated_test_file.parent.mkdir(parents=True, exist_ok=True)
            print(
                f"[MERGE] Consolidating verified tests for module: {relative_target.name}"
            )
            merged_content = [
                "# Generated Modular Pytest Suite",
                "\n".join(sorted(list(all_imports))),
            ]
            if all_fixtures:
                merged_content.append("\n\n".join(all_fixtures))
            merged_content.append("\n\n".join(all_cases))
            consolidated_test_file.write_text(
                "\n\n".join(merged_content) + "\n", encoding="utf-8"
            )
            print(f"  [SUCCESS] Created consolidated file -> {consolidated_test_file}")
