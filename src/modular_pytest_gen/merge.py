import ast
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Set, Dict, Optional

from .config import ProjectConfig
from .layout import LayoutManager

class TestMerger:
    """
    Scans the temporary testing registry, combines isolated unit tests 
    belonging to the same target source script, and builds a clean test file.
    Uses AST parsing to safely append to existing files without duplicating functions.
    """
    def __init__(
        self, config: ProjectConfig, 
        layout_manager: LayoutManager,
        final_test_root: str | Path,
        tmp_dir: Optional[str|Path] = None):
        self.config = config
        self.layout = layout_manager
        self.final_test_root = final_test_root
        if tmp_dir:
            self.tmp_dir = Path(tmp_dir)
        else:
            self.tmp_dir = Path(f"{self.config.layout.test_root}.tmp")

    def merge_all(self):
        final_root = Path(self.final_test_root)
        if not self.tmp_dir.exists():
            print(f"[MERGE] No temporary directory found at {self.tmp_dir}. Skipping merge.")
            return

        # Group verified test files by their original source module
        verified_files = list(self.tmp_dir.rglob("*_verified.py"))
        
        if self.config.layout.granularity == "function":
            for vf in verified_files:
                rel_path = vf.relative_to(self.tmp_dir)
                module_parts = rel_path.parts[:-2]
                func_name = rel_path.parts[-2]
                
                if not module_parts:
                    continue

                # Reconstruct path: final_root / otaf / common / _common / test_function_name.py
                target_dir = final_root.joinpath(*module_parts)
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / f"test_{func_name}.py"

                # Safe overwrite: If it exists, we just overwrite because it's isolated to this function anyway
                shutil.copy2(vf, target_file)
                print(f"  [SUCCESS] Wrote granular test file -> {target_file}")
            return
        
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
                    print(f"  [WARN] Failed to parse verified file {test_script.name}: {e}")

            if not all_cases:
                continue

            consolidated_test_file = self.layout.get_test_file_path(source_path)
            consolidated_test_file.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"[MERGE] Consolidating {len(all_cases)} generated tests for module: {source_path.name}")
            
            # --- AST-Aware Safe Append Logic ---
            if consolidated_test_file.exists():
                print(f"  [INFO] Target file exists. Performing AST-aware safe append...")
                try:
                    existing_content = consolidated_test_file.read_text(encoding="utf-8")
                    existing_tree = ast.parse(existing_content)
                    
                    existing_funcs = {node.name for node in existing_tree.body if isinstance(node, ast.FunctionDef)}
                    existing_imports = {ast.unparse(node) for node in existing_tree.body if isinstance(node, (ast.Import, ast.ImportFrom))}
                    
                    # Filter out duplicates
                    all_imports = all_imports - existing_imports
                    all_fixtures = {k: v for k, v in all_fixtures.items() if k not in existing_funcs}
                    all_cases = {k: v for k, v in all_cases.items() if k not in existing_funcs}
                    
                    if not all_cases and not all_fixtures:
                        print(f"  [SKIP] All generated tests already exist in {consolidated_test_file.name}")
                        continue
                        
                    merged_content = [existing_content, "\n# --- Auto-Generated Additions ---"]
                    if all_imports:
                        merged_content.append("\n".join(sorted(list(all_imports))))
                    if all_fixtures:
                        merged_content.append("\n\n".join(all_fixtures.values()))
                    if all_cases:
                        merged_content.append("\n\n".join(all_cases.values()))
                        
                    consolidated_test_file.write_text("\n\n".join(merged_content) + "\n", encoding="utf-8")
                    print(f"  [SUCCESS] Safely appended {len(all_cases)} new tests to -> {consolidated_test_file.name}")
                    continue
                    
                except Exception as e:
                    print(f"  [ERROR] Failed to parse existing file {consolidated_test_file.name}: {e}. Skipping to prevent corruption.")
                    continue

            # --- Standard Write Logic (New File) ---
            merged_content = [
                '# Generated Modular Pytest Suite',
                "\n".join(sorted(list(all_imports)))
            ]
            
            if all_fixtures:
                merged_content.append("\n\n".join(all_fixtures.values()))
            merged_content.append("\n\n".join(all_cases.values()))
                
            consolidated_test_file.write_text("\n\n".join(merged_content) + "\n", encoding="utf-8")
            print(f"  [SUCCESS] Created new consolidated file -> {consolidated_test_file}")