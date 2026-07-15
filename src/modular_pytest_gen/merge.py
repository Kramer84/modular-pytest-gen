import ast
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional, Set

from .config import ProjectConfig
from .layout import LayoutManager


class TestMerger:
    r"""
    Merge generated test files into the final test suite.

    The `TestMerger` class orchestrates the consolidation of verified test
    files into the final test suite. It handles different layout
    granularities and ensures safe merging of test files without
    duplication.

    Parameters
    ----------
    config : ProjectConfig
        The project configuration containing layout and root directory
        settings.
    layout_manager : LayoutManager
        The layout manager responsible for determining the structure of the
        test suite.
    final_test_root : str | Path
        The root directory where the final test suite will be stored.
    tmp_dir : Optional[str | Path], optional
        The temporary directory containing verified test files. If not
        provided, a default temporary directory is used.

    Methods
    -------
    merge_all :
        Merge all verified test files into the final test suite.

    Raises
    ------
    ValueError
        Raised if the layout granularity specified in the configuration is
        not supported.

    Warnings
    --------
    Ensure that the temporary directory contains verified test files before
    running the merge operation.
    """

    def __init__(
        self,
        config: ProjectConfig,
        layout_manager: LayoutManager,
        final_test_root: str | Path,
        tmp_dir: Optional[str | Path] = None,
    ):
        r"""
        Configure test generator with project settings.

        Constructs a test generator instance with the provided
        configuration, layout manager, and directory paths. The instance
        will manage test generation and execution workflows.

        Warnings
        --------
        Ensure the `final_test_root` directory exists and is writable to
        avoid runtime errors during test generation.

        See Also
        --------
        ProjectConfig :
            Configuration object containing project settings and paths.
        LayoutManager :
            Manager for handling project directory layouts and file
            operations.

        Notes
        -----
        The `tmp_dir` parameter defaults to a temporary directory path
        derived from the project's test root if not specified.
        """

        self.config = config
        self.layout = layout_manager
        self.final_test_root = final_test_root
        if tmp_dir:
            self.tmp_dir = Path(tmp_dir)
        else:
            self.tmp_dir = Path(f"{self.config.layout.test_root}.tmp")

    def merge_all(self):
        r"""
        Merge all verified test files into the final test directory

        This method consolidates verified test files from the temporary
        directory into the final test directory. It handles different
        layout granularities (function, class, module) and ensures no
        duplicate tests are added.

        Returns
        -------
        None
            The method does not return any value.

        Raises
        ------
        ValueError
            If the layout granularity is not one of 'function', 'class', or
            'module'.

        Warns
        -----
        UserWarning
            If a verified file cannot be parsed.
        """

        final_root = Path(self.final_test_root)
        if not self.tmp_dir.exists():
            print(
                f"[MERGE] No temporary directory found at {self.tmp_dir}. Skipping merge."
            )
            return
        verified_files = list(self.tmp_dir.rglob("*_verified.py"))
        if self.config.layout.granularity in ("function", "class"):
            for vf in verified_files:
                rel_path = vf.relative_to(self.tmp_dir)
                module_parts = rel_path.parts[:-2]
                target_name = rel_path.parts[-2]
                if not module_parts:
                    continue
                target_dir = final_root.joinpath(*module_parts)
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / f"test_{target_name}.py"
                shutil.copy2(vf, target_file)
                print(f"  [SUCCESS] Wrote granular test file -> {target_file}")
            return
        elif self.config.layout.granularity == "module":
            module_groups = defaultdict(list)
            for vf in verified_files:
                rel_path = vf.relative_to(self.tmp_dir)
                module_parts = rel_path.parts[:-2]
                if not module_parts:
                    continue
                pseudo_source_rel = Path(*module_parts).with_suffix(".py")
                pseudo_source_full = Path(self.config.source_root) / pseudo_source_rel
                module_groups[pseudo_source_full].append(vf)
            for source_path, test_scripts in module_groups.items():
                all_imports: Set[str] = set()
                all_fixtures: Dict[str, str] = {}
                all_cases: Dict[str, str] = {}
                for test_script in test_scripts:
                    try:
                        content = test_script.read_text(encoding="utf-8")
                        tree = ast.parse(content)
                        for node in tree.body:
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                all_imports.add(ast.unparse(node))
                            elif isinstance(node, ast.FunctionDef):
                                if node.name.startswith("test_"):
                                    all_cases[node.name] = ast.unparse(node)
                                else:
                                    all_fixtures[node.name] = ast.unparse(node)
                            elif isinstance(node, ast.ClassDef):
                                all_fixtures[node.name] = ast.unparse(node)
                            elif isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if isinstance(target, ast.Name):
                                        all_fixtures[target.id] = ast.unparse(node)
                    except Exception as e:
                        print(
                            f"  [WARN] Failed to parse verified file {test_script.name}: {e}"
                        )
                if not all_cases:
                    continue
                consolidated_test_file = self.layout.get_test_file_path(source_path)
                consolidated_test_file.parent.mkdir(parents=True, exist_ok=True)
                print(
                    f"[MERGE] Consolidating {len(all_cases)} generated tests for module: {source_path.name}"
                )
                if consolidated_test_file.exists():
                    print(
                        f"  [INFO] Target file exists. Performing AST-aware safe append..."
                    )
                    try:
                        existing_content = consolidated_test_file.read_text(
                            encoding="utf-8"
                        )
                        existing_tree = ast.parse(existing_content)
                        existing_funcs = {
                            node.name
                            for node in existing_tree.body
                            if isinstance(node, ast.FunctionDef)
                        }
                        existing_imports = {
                            ast.unparse(node)
                            for node in existing_tree.body
                            if isinstance(node, (ast.Import, ast.ImportFrom))
                        }
                        all_imports = all_imports - existing_imports
                        all_fixtures = {
                            k: v
                            for k, v in all_fixtures.items()
                            if k not in existing_funcs
                        }
                        all_cases = {
                            k: v
                            for k, v in all_cases.items()
                            if k not in existing_funcs
                        }
                        if not all_cases and (not all_fixtures):
                            print(
                                f"  [SKIP] All generated tests already exist in {consolidated_test_file.name}"
                            )
                            continue
                        merged_content = [
                            existing_content,
                            "\n# --- Auto-Generated Additions ---",
                        ]
                        if all_imports:
                            merged_content.append("\n".join(sorted(list(all_imports))))
                        if all_fixtures:
                            merged_content.append("\n\n".join(all_fixtures.values()))
                        if all_cases:
                            merged_content.append("\n\n".join(all_cases.values()))
                        consolidated_test_file.write_text(
                            "\n\n".join(merged_content) + "\n", encoding="utf-8"
                        )
                        print(
                            f"  [SUCCESS] Safely appended {len(all_cases)} new tests to -> {consolidated_test_file.name}"
                        )
                        continue
                    except Exception as e:
                        print(
                            f"  [ERROR] Failed to parse existing file {consolidated_test_file.name}: {e}. Skipping to prevent corruption."
                        )
                        continue
                merged_content = [
                    "# Generated Modular Pytest Suite",
                    "\n".join(sorted(list(all_imports))),
                ]
                if all_fixtures:
                    merged_content.append("\n\n".join(all_fixtures.values()))
                merged_content.append("\n\n".join(all_cases.values()))
                consolidated_test_file.write_text(
                    "\n\n".join(merged_content) + "\n", encoding="utf-8"
                )
                print(
                    f"  [SUCCESS] Created new consolidated file -> {consolidated_test_file}"
                )
        else:
            raise ValueError(
                f"Unsupported layout granularity: '{self.config.layout.granularity}'. Must be one of: 'function', 'class', or 'module'."
            )
