import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from .config import load_config, ProjectConfig
from .layout import LayoutManager
from .resolver import ImportResolver
from .parser import ModuleParser
from .prompter import PromptBuilder
from .client import OllamaClient, MistralClient


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
        
        # Resolve exception paths so the LLM knows how to import them
        for exc in analysis["exceptions"]:
            try:
                exc["import_path"] = resolver.get_import_path(path, exc["name"])
            except ValueError:
                exc["import_path"] = exc["name"]
        
        context["exceptions"].extend(analysis["exceptions"])
        
    return context


def main():
    parser = argparse.ArgumentParser(description="Modular Pytest Generator using LLMs.")
    parser.add_argument("--config", type=str, default="autotest.toml", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Generate prompt Markdowns instead of calling the LLM.")
    
    # Overrides for TOML config
    parser.add_argument("--provider", type=str, choices=["ollama", "mistral"], help="LLM Provider override")
    parser.add_argument("--model", type=str, help="Model tag override")
    parser.add_argument("--structured", action="store_true", help="Force Tool/JSON output mode override")
    
    args = parser.parse_args()

    # 1. Initialize Core Engines
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"[FATAL] Configuration error: {e}")
        sys.exit(1)

    layout = LayoutManager(config)
    resolver = ImportResolver(config.source_root, config.import_prefix)
    
    # Merge CLI args with TOML LLM config
    provider = args.provider or config.llm.provider
    model = args.model or config.llm.model
    structured = args.structured or config.llm.structured
    
    client = None
    if not args.dry_run:
        try:
            if provider == "mistral":
                client = MistralClient(model=model)
            else:
                client = OllamaClient(host=config.llm.host, model=model)
        except Exception as e:
            print(f"[FATAL] Client initialization failed: {e}")
            sys.exit(1)
            
    prompter = PromptBuilder(structured_output=structured)
    
    # 2. Extract Framework Context
    print("Aggregating global framework context...")
    global_context = gather_global_context(config, resolver)

    source_root = Path(config.source_root).resolve()
    if not source_root.exists():
        print(f"[FATAL] Source root '{source_root}' does not exist.")
        sys.exit(1)

    # 3. Execution Loop
    for target_file in source_root.rglob("*.py"):
        if target_file.name == "__init__.py":
            continue
            
        if any(target_file.match(pattern) for pattern in config.discovery.exclude_patterns):
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

        # 4. Function Processing Loop
        for func in functions_to_test:
            if func["name"] in config.discovery.exclude_functions:
                print(f"  -> Skipping function: {func['name']} (Blacklisted)")
                continue

            print(f"  -> Processing: {func['name']}")
            
            try:
                logical_import_path = resolver.get_import_path(target_file, func["name"])
            except ValueError:
                logical_import_path = func["name"]

            system_prompt = prompter.build_system_prompt(global_context, logical_import_path)
            user_prompt = prompter.build_user_prompt(func)
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

            # Check and inject required imports to avoid NameErrors
            module_logical_path = ".".join(logical_import_path.split(".")[:-1])
            if module_logical_path:
                import_stmt = f"from {module_logical_path} import {func['name']}\n"
                current_contents = test_path.read_text(encoding="utf-8")
                if import_stmt not in current_contents:
                    with open(test_path, "a", encoding="utf-8") as f:
                        f.write(import_stmt)

            try:
                test_code = client.generate_test(system_prompt, user_prompt, tool_schema)
                if test_code:
                    with open(test_path, "a", encoding="utf-8") as f:
                        f.write(f"\n\n# Tests for {func['name']}\n")
                        f.write(test_code)
                        f.write("\n")
                else:
                    print(f"  [WARN] LLM returned empty code block for {func['name']}")
            except Exception as e:
                print(f"  [ERROR] Failed to generate tests for {func['name']}: {e}")

if __name__ == "__main__":
    main()