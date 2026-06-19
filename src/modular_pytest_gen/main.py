import argparse
import sys
from pathlib import Path
from typing import Any, Dict
from copy import deepcopy

from .config import load_config, ProjectConfig
from .layout import LayoutManager
from .resolver import ImportResolver
from .parser import ModuleParser
from .prompter import PromptBuilder
from .client import OllamaClient, MistralClient, unload_ollama_model
from .validator import TestValidator
from .merge import TestMerger

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def gather_global_context(config: ProjectConfig, resolver: ImportResolver) -> Dict[str, Any]:
    """Compiles constants and exceptions from specific files to feed the LLM."""
    context = {"constants": {}, "exceptions": []}
    for file_path in config.global_context:
        path = Path(file_path)
        if not path.exists():
            print(f"[WARN] Global context file not found: {path}")
            continue
        parser = ModuleParser(path)
        analysis = parser.parse()
        context["constants"].update(analysis["constants"])
        for exc in analysis["exceptions"]:
            try:
                exc["import_path"] = resolver.get_import_path(path, exc["name"])
            except ValueError:
                exc["import_path"] = exc["name"]
        context["exceptions"].extend(analysis["exceptions"])
    return context

def init_project(args):
    """
    Handles the `init` CLI command.
    Generates a default autotest.toml, inferring settings from pyproject.toml if present.
    """
    config_path = Path("autotest.toml")
    if config_path.exists() and not args.force:
        print("[ERROR] autotest.toml already exists. Use --force to overwrite.")
        sys.exit(1)

    import_prefix = "my_package"
    source_root = "src"

    target_pyproject = Path("pyproject.toml")
    if target_pyproject.exists() and tomllib is not None:
        try:
            with open(target_pyproject, "rb") as f:
                data = tomllib.load(f)
            
            project_name = data.get("project", {}).get("name")
            if project_name:
                import_prefix = project_name.replace("-", "_")
                print(f"[INIT] Inferred import_prefix '{import_prefix}' from project name.")

            setuptools_where = data.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {}).get("where", [])
            if setuptools_where and isinstance(setuptools_where, list):
                source_root = setuptools_where[0]
                print(f"[INIT] Inferred source_root '{source_root}' from setuptools config.")
            elif Path("src").exists():
                source_root = "src"
                print("[INIT] Detected 'src' directory, using as source_root.")
            elif Path(import_prefix).exists():
                source_root = "."
                print(f"[INIT] Detected flat layout directory '{import_prefix}', using '.' as source_root.")
                
        except Exception as e:
            print(f"[WARN] Failed to parse pyproject.toml for inference: {e}")

    template = f"""# autotest.toml - Modular Pytest Gen Configuration

source_root = "{source_root}"

import_prefix = "{import_prefix}"

global_context = []

custom_instructions = ""

[layout]
strategy = "external" 

structure = "nested"  

test_root = "tests"

[discovery]
respect_dunder_all = true

exclude_patterns = [
    "*__init__.py",
    "build",
    "tests",
    "*test_*.py"
]

exclude_functions = []

[llm]
provider = "ollama"

model = "qwen2.5-coder:7b-instruct-q8_0"

host = "http://localhost:11434"

structured = false
"""
    config_path.write_text(template, encoding="utf-8")
    print("[SUCCESS] Initialized autotest.toml with inferred defaults.")

def run_generation(args):
    """
    Handles the `run` CLI command.
    Executes the AST scanning, path resolution, and LLM prompting loop.
    """
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"[FATAL] Configuration error: {e}")
        sys.exit(1)

    if args.verbose:
        print(f"[DEBUG] Loaded configuration: {config}")

    llm_model = args.model or config.llm.model
    provider = args.provider or config.llm.provider

    layout = LayoutManager(config)
    resolver = ImportResolver(config.source_root, config.import_prefix)
    
    if args.verbose:
        print(f"[DEBUG] Resolver: {resolver}")

    structured = args.structured or config.llm.structured
    
    client = None
    if not args.dry_run:
        try:
            if provider == "mistral":
                client = MistralClient(model=llm_model)
            else:
                client = OllamaClient(host=config.llm.host, model=llm_model)
        except Exception as e:
            print(f"[FATAL] Client initialization failed: {e}")
            sys.exit(1)
            
    prompter = PromptBuilder(structured_output=structured)
    validator = TestValidator(config)

    print("Aggregating global framework context...")
    global_context = gather_global_context(config, resolver)

    if args.verbose:
        print(f"[DEBUG] Global context: {global_context}")

    source_root = Path(config.source_root).resolve()
    if not source_root.exists():
        print(f"[FATAL] Source root '{source_root}' does not exist.")
        sys.exit(1)

    print("Building internal project metadata registry...")
    project_wide_context = {"constants": {}, "exceptions": {}}
    
    for py_file in source_root.rglob("*.py"):
        try:
            analysis = ModuleParser(py_file).parse()
            # Store constants
            for const_name, const_val in analysis["constants"].items():
                project_wide_context["constants"][const_name] = const_val
            # Store exceptions mapped by class name
            for exc in analysis["exceptions"]:
                project_wide_context["exceptions"][exc["name"]] = exc
        except Exception:
            continue
    
    if args.verbose:
        print(f"[DEBUG] Project-wide context: {str(project_wide_context)[:500]}+...")  # Truncated for brevity

    try:

        for target_file in source_root.rglob("*.py"):
            if target_file.name == "__init__.py":
                continue
                
            rel_path = target_file.relative_to(source_root)
            
            should_exclude = False
            for pattern in config.discovery.exclude_patterns:
                if pattern in rel_path.parts:
                    should_exclude = True
                    break
                if target_file.match(pattern):
                    should_exclude = True
                    break
                    
            if should_exclude:
                continue

            print(f"\nScanning: {target_file}")
            module_analysis = ModuleParser(target_file).parse()
            
            if module_analysis["flags"]["profile"] in ["CONSTANT_REGISTRY", "EXCEPTION_REGISTRY"]:
                print("  -> Skipping: Static profile detected.")
                continue

            functions_to_test = module_analysis["functions"]
            if config.discovery.respect_dunder_all and module_analysis["flags"]["has_dunder_all"]:
                valid_names = set(module_analysis["dunder_all"])
                functions_to_test = [f for f in functions_to_test if f["name"] in valid_names]

            if not functions_to_test:
                continue

            test_path = layout.get_test_file_path(target_file)
            test_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not args.dry_run and not test_path.exists():
                test_path.write_text("import pytest\n\n", encoding="utf-8")

            for func in functions_to_test:
                if func["name"] in config.discovery.exclude_functions:
                    print(f"  -> Skipping function: {func['name']} (Blacklisted)")
                    continue

                print(f"  -> Processing: {func['name']}")
                
                try:
                    logical_import_path = resolver.get_import_path(target_file, func["name"])
                except ValueError:
                    logical_import_path = func["name"]

                module_logical_path = ".".join(logical_import_path.split(".")[:-1]) 
                if module_logical_path:
                    function_import_statement = f"from {module_logical_path} import {func['name']}"
                else:
                    function_import_statement = f"import {func['name']}"

                # Prepend any third-party/external imports discovered via AST tracking
                import_statement = "\n".join(func["external_imports"]) if func.get("external_imports") else ""

                # Dynamically assemble the global context for THIS specific function window
                targeted_global_context = {"constants": {}, "exceptions": []}
                
                # Read the comprehensive, extended name registry array from the metadata payload
                for name in func.get("used_names", []):
                    if name in project_wide_context["constants"]:
                        targeted_global_context["constants"][name] = project_wide_context["constants"][name]
                    if name in project_wide_context["exceptions"]:
                        exc_meta = deepcopy(project_wide_context["exceptions"][name])
                        try:
                            exc_meta["import_path"] = resolver.get_import_path(target_file, name)
                        except ValueError:
                            exc_meta["import_path"] = name
                        targeted_global_context["exceptions"].append(exc_meta)

                system_prompt = prompter.build_system_prompt(targeted_global_context, logical_import_path)
                user_prompt = prompter.build_user_prompt(func, function_import_statement, import_statement, custom_instructions=config.custom_instructions)
                tool_schema = prompter.get_tool_schema() if structured else None

                if args.dry_run:
                    dry_dir = Path("dry_run_prompts")
                    dry_dir.mkdir(exist_ok=True)
                    md_path = dry_dir / f"{target_file.stem}_{func['name']}.md"
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(f"# System Prompt\n\n```text\n{system_prompt}\n```\n\n")
                        f.write(f"# User Prompt\n\n```text\n{user_prompt}\n```\n\n")
                        if tool_schema:
                            import json
                            f.write(f"# Tool Schema\n\n```json\n{json.dumps(tool_schema, indent=2)}\n```\n")
                    print(f"  [DRY RUN] Generated prompt -> {md_path}")
                    continue

                # Execute our standalone file preservation validation runner pass
                validator.validate_and_heal(
                    target_file=target_file,
                    source_root=source_root,
                    func_metadata=func,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    import_statement=import_statement,
                    function_import_statement=function_import_statement,
                    client=client,
                    tool_schema=tool_schema
                )

        # --- FINAL PHASE: Execute the script compilation consolidation merge ---
        if not args.dry_run:
            print("\n==============================================")
            print("Beginning final test suite script consolidation pass...")
            merger = TestMerger(tmp_dir=f"{config.layout.test_root}.tmp")
            merger.merge_all(final_test_root=config.layout.test_root)

    except KeyboardInterrupt:
        print("\n[PROCESS] Execution halted by user command interrupt request (Ctrl+C).")
    finally:
        # Guarantee model compute resources clear if running an Ollama service target instance
        if not args.dry_run and provider == "ollama":
            unload_ollama_model(llm_model)
def cli_entry():
    parser = argparse.ArgumentParser(description="Modular Pytest Generator using LLMs.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize autotest.toml configuration file.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing autotest.toml if present")

    run_parser = subparsers.add_parser("run", help="Generate pytest files.")
    run_parser.add_argument("--config", type=str, default="autotest.toml", help="Path to config file")
    run_parser.add_argument("--dry-run", action="store_true", help="Generate prompt Markdowns instead of calling the LLM.")
    
    run_parser.add_argument("--provider", type=str, choices=["ollama", "mistral"], help="LLM Provider override")
    run_parser.add_argument("--model", type=str, help="Model tag override")
    run_parser.add_argument("--structured", action="store_true", help="Force Tool/JSON output mode override")

    args = parser.parse_args()

    if args.command == "init":
        init_project(args)
    elif args.command == "run":
        run_generation(args)

if __name__ == "__main__":
    cli_entry()