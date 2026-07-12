import sys
import ast
import importlib
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

import typer

from ..client import MistralClient, OllamaClient, unload_ollama_model
from ..config import ProjectConfig, load_config
from ..layout import LayoutManager
from ..merge import TestMerger
from ..parser import ModuleParser
from ..prompter import PromptBuilder
from ..resolver import ImportResolver
from ..validator import TestValidator


def gather_global_context(
    config: ProjectConfig, resolver: ImportResolver
) -> Dict[str, Any]:
    """Compiles constants and exceptions from specific files to feed the LLM."""
    context: Dict[str, Any] = {"constants": {}, "exceptions": []}
    for file_path in config.global_context:
        path = Path(file_path)
        if not path.exists():
            typer.secho(
                f"[WARN] Global context file not found: {path}", fg=typer.colors.YELLOW
            )
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


def run_app(
    config_path: Annotated[
        str, typer.Option("--config", "-c", help="Path to config file")
    ] = "autotest.toml",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Generate prompt Markdowns instead of calling the LLM"
        ),
    ] = False,
    include_classes: Annotated[bool, typer.Option("--include-classes", help="Generate tests for classes as well as functions.")] = False,
    max_class_lines: Annotated[int, typer.Option("--max-class-lines", help="Skip classes larger than this many lines.")] = 300,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force test generation even if verified tests already exist.")] = False,
    provider: Annotated[
        Optional[str], typer.Option(help="LLM Provider override")
    ] = None,
    model: Annotated[Optional[str], typer.Option(help="Model tag override")] = None,
    structured: Annotated[
        bool, typer.Option(help="Force Tool/JSON output mode override")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output for debugging"),
    ] = False,
    merge_tests : Annotated[
        bool,
        typer.Option("--merge-tests", "-m", help="Merge generated test files into a single suite")
    ] = False,
):
    try:
        config = load_config(config_path)
    except Exception as e:
        typer.secho(f"[FATAL] Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if verbose:
        typer.echo(f"[DEBUG] Loaded configuration: {config}")
    llm_model = model or config.llm.model
    active_provider = provider or config.llm.provider
    layout = LayoutManager(config)
    resolver = ImportResolver(config.source_root, config.import_prefix)
    if verbose:
        typer.echo(f"[DEBUG] Resolver: {resolver}")
    try:
        if config.import_prefix:
            importlib.import_module(config.import_prefix)
            typer.echo(f"[OK] Successfully imported main module '{config.import_prefix}'.")
    except ImportError:
        typer.secho(f"\n[FATAL] Cannot import module '{config.import_prefix}'.", fg=typer.colors.RED)
        typer.secho("Ensure your virtual environment is activated and the target package is installed (e.g., `pip install -e .`).", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    is_structured = structured or config.llm.structured
    client = None
    if not dry_run:
        try:
            if active_provider == "mistral":
                client = MistralClient(model=llm_model)
            else:
                client = OllamaClient(host=config.llm.host, model=llm_model)
        except Exception as e:
            typer.secho(
                f"[FATAL] Client initialization failed: {e}", fg=typer.colors.RED
            )
            raise typer.Exit(code=1)
    prompter = PromptBuilder(structured_output=is_structured)
    validator = TestValidator(config)
    typer.echo("Aggregating global framework context...")
    global_context = gather_global_context(config, resolver)
    if verbose:
        typer.echo(f"[DEBUG] Global context: {global_context}")
    source_root = Path(config.source_root).resolve()
    if not source_root.exists():
        typer.secho(
            f"[FATAL] Source root '{source_root}' does not exist.", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)
    typer.echo("Building internal project metadata registry...")
    project_wide_context: Dict[str, Any] = {"constants": {}, "exceptions": {}}
    for py_file in source_root.rglob("*.py"):
        try:
            analysis = ModuleParser(py_file).parse()
            for const_name, const_val in analysis["constants"].items():
                project_wide_context["constants"][const_name] = const_val
            for exc in analysis["exceptions"]:
                project_wide_context["exceptions"][exc["name"]] = exc
        except Exception:
            continue
    try:
        for target_file in source_root.rglob("*.py"):
            if target_file.name == "__init__.py":
                continue
            rel_path = target_file.relative_to(source_root)
            should_exclude = False
            for pattern in config.discovery.exclude_patterns:
                if pattern in rel_path.parts or target_file.match(pattern):
                    should_exclude = True
                    break
            if should_exclude:
                continue
            typer.echo(f"\nScanning: {target_file}")
            module_analysis = ModuleParser(target_file).parse()
            if module_analysis["flags"]["profile"] in [
                "CONSTANT_REGISTRY",
                "EXCEPTION_REGISTRY",
            ]:
                typer.echo("  -> Skipping: Static profile detected.")
                continue
            targets_to_test = module_analysis["functions"]
            if include_classes:
                for cls in module_analysis["classes"]:
                    line_count = len(cls["code"].splitlines())
                    if line_count <= max_class_lines:
                        targets_to_test.append(cls)
                    else:
                        typer.echo(f"  -> Skipping class: {cls['name']} ({line_count} lines exceeds max {max_class_lines})")
            
            if (
                config.discovery.respect_dunder_all
                and module_analysis["flags"]["has_dunder_all"]
            ):
                valid_names = set(module_analysis["dunder_all"])
                targets_to_test = [
                    f for f in targets_to_test if f["name"] in valid_names
                ]
            if not targets_to_test:
                continue
            for target in targets_to_test:
                if target["name"] in config.discovery.exclude_functions:
                    typer.echo(f"  -> Skipping target: {target['name']} (Blacklisted)")
                    continue
                if not force:
                    # 1. Check Temporary Directory
                    rel_module_path = target_file.relative_to(source_root).with_suffix("")
                    func_tmp_dir = Path(f"{config.layout.test_root}.tmp") / rel_module_path / target["name"]
                    is_verified_in_tmp = func_tmp_dir.exists() and any(func_tmp_dir.glob("*_verified.py"))
                    
                    # 2. Check Final Merged Suite
                    is_verified_in_final = False
                    final_test_file = layout.get_test_file_path(target_file)
                    if final_test_file.exists():
                        try:
                            tree = ast.parse(final_test_file.read_text(encoding="utf-8"))
                            existing_funcs = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
                            # Check if any existing test function name contains the target's name
                            if any(target["name"] in f for f in existing_funcs if f.startswith("test_")):
                                is_verified_in_final = True
                        except Exception:
                            pass # Safely ignore unparseable test files
                            
                    if is_verified_in_tmp or is_verified_in_final:
                        typer.echo(f"  -> Skipping target: {target['name']} (Already verified)")
                        continue
                typer.echo(f"  -> Processing: {target['name']}")
                try:
                    logical_import_path = resolver.get_import_path(
                        target_file, target["name"]
                    )
                except ValueError:
                    logical_import_path = target["name"]
                module_logical_path = ".".join(logical_import_path.split(".")[:-1])
                if module_logical_path:
                    function_import_statement = (
                        f"from {module_logical_path} import {target['name']}"
                    )
                else:
                    function_import_statement = f"import {target['name']}"
                import_statement = (
                    "\n".join(target["external_imports"])
                    if target.get("external_imports")
                    else ""
                )
                targeted_global_context: Dict[str, Any] = {"constants": {}, "exceptions": []}
                for name in target.get("used_names", []):
                    if name in project_wide_context["constants"]:
                        targeted_global_context["constants"][name] = (
                            project_wide_context["constants"][name]
                        )
                    if name in project_wide_context["exceptions"]:
                        exc_meta = deepcopy(project_wide_context["exceptions"][name])
                        try:
                            exc_meta["import_path"] = resolver.get_import_path(
                                target_file, name
                            )
                        except ValueError:
                            exc_meta["import_path"] = name
                        targeted_global_context["exceptions"].append(exc_meta)
                system_prompt = prompter.build_system_prompt(
                    targeted_global_context, logical_import_path
                )
                user_prompt = prompter.build_user_prompt(
                    target,
                    function_import_statement,
                    import_statement,
                    custom_instructions=config.custom_instructions,
                )
                tool_schema = prompter.get_tool_schema() if is_structured else None
                if dry_run:
                    dry_dir = Path("dry_run_prompts")
                    dry_dir.mkdir(exist_ok=True)
                    md_path = dry_dir / f"{target_file.stem}_{target['name']}.md"
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(f"# System Prompt\n\n```text\n{system_prompt}\n```\n\n")
                        f.write(f"# User Prompt\n\n```text\n{user_prompt}\n```\n\n")
                        if tool_schema:
                            import json

                            f.write(
                                f"# Tool Schema\n\n```json\n{json.dumps(tool_schema, indent=2)}\n```\n"
                            )
                    typer.echo(f"  [DRY RUN] Generated prompt -> {md_path}")
                    continue
                validator.validate_and_heal(
                    target_file=target_file,
                    source_root=source_root,
                    func_metadata=target,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    import_statement=import_statement,
                    function_import_statement=function_import_statement,
                    client=client,
                    tool_schema=tool_schema,
                )
        if not dry_run and merge_tests:
            typer.echo("\n==============================================")
            typer.echo("Beginning final test suite script consolidation pass...")
            merger = TestMerger(config=config, layout_manager=layout)
            merger.merge_all()
    except KeyboardInterrupt:
        typer.secho(
            "\n[PROCESS] Execution halted by user command interrupt request (Ctrl+C).",
            fg=typer.colors.YELLOW,
        )
    finally:
        if not dry_run and active_provider == "ollama":
            unload_ollama_model(llm_model)
