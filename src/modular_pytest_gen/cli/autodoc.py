import json
import re
import typer
from pathlib import Path
from typing import Annotated, Dict, Any, Optional

from ..config import load_config
from ..resolver import ImportResolver
from ..parser import ModuleParser
from ..graph import DependencyGraph
from ..injector import inject_autodoc
from ..client import OllamaClient, MistralClient
from .. import templates  # <--- Import templates

def get_autodoc_tool_schema() -> dict:
    """Returns the JSON schema for the autodoc tool calling."""
    return {
        "type": "function",
        "function": {
            "name": "write_autodoc",
            "description": "Outputs the generated docstring, the upgraded function signature, and any required imports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "docstring": {
                        "type": "string",
                        "description": "The raw docstring text, formatted in strict NumPy style. Do not include the surrounding triple quotes."
                    },
                    "updated_signature": {
                        "type": "string",
                        "description": "The complete function signature with upgraded, Beartype-compliant type annotations (e.g., 'def my_func(x: int) -> list[str]:')."
                    },
                    "required_imports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of exact import statements required for the updated type hints (e.g., ['from beartype.typing import Optional', 'from numpy.typing import NDArray']). Leave empty if none are needed."
                    }
                },
                "required": ["docstring", "updated_signature", "required_imports"]
            }
        }
    }


def autodoc_app(
    config_path: Annotated[str, typer.Option("--config", "-c", help="Path to config file")] = "autotest.toml",
    mode: Annotated[str, typer.Option("--mode", "-m", help="'generate' (missing docstrings) or 'verify' (correct existing docstrings).")] = "generate",
    examples: Annotated[bool, typer.Option("--examples", help="Force the LLM to generate an Examples block.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate prompt Markdowns without calling the LLM.")] = False,
    output_dir: Annotated[str, typer.Option("--output-dir", "-o", help="Directory to stage modified files for manual verification instead of overwriting in-place.")] = "",
    provider: Annotated[str, typer.Option(help="LLM Provider override")] = "",
    model: Annotated[str, typer.Option(help="Model tag override")] = "",
):
    if mode not in ["generate", "verify"]:
        typer.secho("Mode must be 'generate' or 'verify'.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        config = load_config(config_path)
    except Exception as e:
        typer.secho(f"[FATAL] Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    source_root = Path(config.source_root).resolve()
    resolver = ImportResolver(config.source_root, config.import_prefix)
    graph = DependencyGraph()

    llm_model = model or config.llm.model
    active_provider = provider or config.llm.provider
    
    client = None
    if not dry_run:
        client = MistralClient(model=llm_model) if active_provider == "mistral" else OllamaClient(host=config.llm.host, model=llm_model)

    # --- Load Global Context ---
    readme_path = Path("README.md")

    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        
        # findall extracts all matching sections into a list of strings
        matches = re.findall(
            r"<!--\s*START_CONTEXT\s*-->(.*?)<!--\s*END_CONTEXT\s*-->", 
            readme_text, 
            re.DOTALL
        )
        
        if matches:
            # Join all captured blocks together with a couple of newlines separating them
            readme_context = "\n\n".join(block.strip() for block in matches)
        else:
            # Fallback to a slice or full text if someone accidentally deletes the tags
            readme_context = readme_text[:2000] 
    else:
        readme_context = "No global context available."

    examples_directive = (
        "Include a concise 'Examples' block showing standard usage." 
        if examples else 
        "Do not include an 'Examples' block unless necessary."
    )
    
    typer.echo("Building project dependency graph...")

    function_registry: Dict[str, Dict[str, Any]] = {}
    known_project_symbols = set()
    
    for file_str, defined_names in resolver.file_definitions.items():
        logical_mod = resolver.physical_to_logical.get(file_str)
        if logical_mod:
            for obj_name in defined_names:
                known_project_symbols.add(f"{logical_mod}.{obj_name}")

    for target_file in source_root.rglob("*.py"):
        if target_file.name == "__init__.py":
            continue
            
        analysis = ModuleParser(target_file).parse()
        
        for func in analysis["functions"]:
            try:
                func_logical_path = resolver.get_import_path(target_file, func["name"])
            except ValueError:
                func_logical_path = func["name"]
                
            func["_file_path"] = target_file
            function_registry[func_logical_path] = func

            dependencies = []
            for used_name in func["used_names"]:
                try:
                    dep_path = resolver.get_import_path(target_file, used_name)
                    if dep_path in known_project_symbols and dep_path != func_logical_path:
                        dependencies.append(dep_path)
                except ValueError:
                    pass
                    
            graph.add_node(func_logical_path, dependencies)

    try:
        execution_order = graph.get_bottom_up_order()
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    generated_docstrings_cache: Dict[str, str] = {}
    typer.echo(f"\nBeginning context-aware docstring injection (Mode: {mode.upper()})...")
    
    for node_path in execution_order:
        if node_path not in function_registry:
            continue
            
        target = function_registry[node_path]
        file_path = target["_file_path"]
        
        # --- Mode Routing Logic ---
        has_docstring = bool(target["docstring"])
        if mode == "generate" and has_docstring:
            generated_docstrings_cache[node_path] = target["docstring"]
            continue
        if mode == "verify" and not has_docstring:
            continue

        typer.echo(f"  -> Processing: {node_path}")

        dependency_context = ""
        for used_name in target["used_names"]:
            try:
                dep_path = resolver.get_import_path(file_path, used_name)
                if dep_path in generated_docstrings_cache:
                    dependency_context += f"\n--- Dependency: {dep_path} ---\n{generated_docstrings_cache[dep_path]}\n"
            except ValueError:
                pass

        # --- Prompt Assembly ---
        system_prompt = templates.AUTODOC_SYSTEM_PROMPT.format(style_guide=templates.NUMPY_STYLE_GUIDE,
                                                               beartype_guide = templates.BEARTYPE_STYLE_GUIDE)
        
        if mode == "generate":
            user_prompt = templates.AUTODOC_GENERATE_USER.format(
                examples_directive=examples_directive,
                readme_context=readme_context,
                signature=target['signature'],
                code=target['code'],
                dependency_context=dependency_context if dependency_context else "None"
            )
        else: # verify
            user_prompt = templates.AUTODOC_VERIFY_USER.format(
                examples_directive=examples_directive,
                readme_context=readme_context,
                signature=target['signature'],
                code=target['code'],
                existing_docstring=target['docstring']
            )
            
        if dry_run:
            dry_dir = Path("dry_run_autodoc_prompts")
            dry_dir.mkdir(exist_ok=True)
            md_path = dry_dir / f"{file_path.stem}_{target['name']}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# System Prompt\n\n```text\n{system_prompt}\n```\n\n")
                f.write(f"# User Prompt\n\n```text\n{user_prompt}\n```\n")
            
            generated_docstrings_cache[node_path] = target["docstring"] if has_docstring else f"[DRY RUN: Simulated docstring for {target['name']}]"
            typer.echo(f"     [DRY RUN] Generated prompt -> {md_path}")
            continue

        try:
            tool_schema = get_autodoc_tool_schema()
            raw_response = client.generate_test(system_prompt, user_prompt, temperature=0.1, tool_schema=tool_schema)
            
            # Failsafe payload extraction
            payload_str = raw_response
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                payload_str = match.group(0)
                
            payload = json.loads(payload_str)
            if "arguments" in payload:
                payload = payload["arguments"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
            
            new_docstring = payload.get("docstring", "")
            updated_signature = payload.get("updated_signature", "")
            required_imports = payload.get("required_imports", [])
            
            ## --- NEW: Aggressive LLM Hallucination Stripping ---
            
            # 1. Clean Docstring: Strip markdown blocks and triple quotes
            new_docstring = re.sub(r"^```(python|text)?\n?", "", new_docstring, flags=re.IGNORECASE)
            new_docstring = re.sub(r"\n?```$", "", new_docstring)
            new_docstring = re.sub(r'^r?["\']{3}\n?', '', new_docstring)
            new_docstring = re.sub(r'\n?["\']{3}$', '', new_docstring)
            new_docstring = new_docstring.strip()

            # 2. Clean Signature: Strip markdown blocks
            updated_signature = re.sub(r"^```(python)?\n?", "", updated_signature, flags=re.IGNORECASE)
            updated_signature = re.sub(r"\n?```$", "", updated_signature)
            updated_signature = updated_signature.strip('` \n')

            # 3. Clean Imports: Strip markdown and split accidental multi-line elements
            clean_imports = []
            for imp in required_imports:
                imp = re.sub(r"^```(python)?\n?", "", imp, flags=re.IGNORECASE)
                imp = re.sub(r"\n?```$", "", imp)
                imp = imp.strip('` \n')
                if imp:
                    # Sometimes the LLM puts multiple imports in one array element
                    clean_imports.extend([i.strip() for i in imp.splitlines() if i.strip()])
            required_imports = clean_imports
            # ---------------------------------------------------

            # Read source code early to calculate dynamic depth
            if output_dir:
                out_dir_path = Path(output_dir).resolve()
                rel_path = file_path.relative_to(source_root)
                write_path = out_dir_path / rel_path
                write_path.parent.mkdir(parents=True, exist_ok=True)
                source_code = write_path.read_text(encoding="utf-8") if write_path.exists() else file_path.read_text(encoding="utf-8")
            else:
                write_path = file_path
                source_code = file_path.read_text(encoding="utf-8")

            # --- NEW: Dynamic Indentation & Hard Wrapping ---
            if new_docstring:
                new_docstring = new_docstring.strip('`').strip('"').strip("'").strip()
                base_indent = 4
                
                # Scan the file to find the exact column offset of this function/method
                for line in source_code.splitlines():
                    if re.match(rf"^\s*(async\s+)?def\s+{target['name']}\s*\(", line):
                        base_indent = len(line) - len(line.lstrip()) + 4
                        break
                        
                from ..injector import format_docstring
                new_docstring = format_docstring(new_docstring, base_indent=base_indent, max_line_length=78)
            # ------------------------------------------------

            modified_source = inject_autodoc(
                source_code, 
                target["name"], 
                new_docstring, 
                updated_signature, 
                required_imports
            )
            
            write_path.write_text(modified_source, encoding="utf-8")
            
            # Ruff Janitor Pass
            import subprocess
            try:
                subprocess.run(["python", "-m", "ruff", "check", str(write_path), "--fix", "--select", "F401,F811"], capture_output=True, check=False)
            except Exception:
                pass 
            
            generated_docstrings_cache[node_path] = new_docstring
            typer.secho(f"     [INJECTED & CLEANED] Successfully wrote to {write_path.name}", fg=typer.colors.GREEN)
            
        except Exception as e:
            typer.secho(f"     [ERROR] Failed to inject autodoc: {e}", fg=typer.colors.RED)

    typer.echo("\n[SUCCESS] Autodoc pipeline complete.")