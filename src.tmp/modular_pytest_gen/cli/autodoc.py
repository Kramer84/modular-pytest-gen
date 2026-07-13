import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

import typer

from .. import templates
from ..client import MistralClient, OllamaClient
from ..config import load_config
from ..docstring import NumpyDocstringSchema, build_numpy_docstring
from ..graph import DependencyGraph
from ..injector import inject_autodoc
from ..parser import ModuleParser
from ..resolver import ImportResolver


def get_autodoc_tool_schema() -> dict:
    r"""
    Retrieve the JSON schema for the autodoc tool
    
    This function returns the JSON schema that defines the structure and
    validation rules for the autodoc tool's parameters. The schema is used
    to ensure that the parameters provided to the autodoc tool are valid
    and correctly formatted.
    
    Returns
    -------
    dict
        The JSON schema for the autodoc tool, which includes the type,
        function name, description, and parameters schema.
    """
    if hasattr(NumpyDocstringSchema, "model_json_schema"):
        parameters_schema = NumpyDocstringSchema.model_json_schema()
    else:
        parameters_schema = NumpyDocstringSchema.schema()
    return {
        "type": "function",
        "function": {
            "name": "write_autodoc",
            "description": "Outputs the granular docstring components, the upgraded function signature, and any required imports.",
            "parameters": parameters_schema,
        },
    }


def autodoc_app(
    config_path: str = 'autotest.toml', mode: str = 'generate', examples: bool = False, dry_run: bool = False, output_dir: str = '', provider: str = '', model: str = '', verbose: bool = False, title_model: str = 'llama3.1:8B') -> None:
    r"""
    Generate docstrings from llm prompts
    
    This function orchestrates the automated docstring generation process
    by building dependency graphs, constructing context-aware prompts, and
    injecting the generated docstrings back into the source code. It
    supports both generation of new docstrings and verification of existing
    ones.
    
    Parameters
    ----------
    config_path : str, optional (default is 'autotest.toml')
        Path to the configuration file
    mode : {"'generate'", "'verify'"}, optional (default is 'generate')
        Operation mode
    examples : bool, optional (default is False)
        Flag to force generation of examples block
    dry_run : bool, optional (default is False)
        Flag to generate prompts without calling LLM
    output_dir : str, optional (default is '')
        Directory to stage modified files
    provider : str, optional (default is '')
        LLM provider override
    model : str, optional (default is '')
        Model tag override
    verbose : bool, optional (default is False)
        Enable verbose debug logging
    title_model : str, optional (default is 'llama3.1:8B')
        Secondary local model for title compression
    
    Returns
    -------
    None
        Generate and inject context-aware docstrings into Python functions
        based on the provided configuration and mode.
    
    Raises
    ------
    typer.Exit : typer.Exit
        If the mode is invalid or if there's a configuration error.
    
    See Also
    --------
    modular_pytest_gen.cli.autodoc.get_autodoc_tool_schema :
        Retrieves the JSON schema for the autodoc tool.
    
    Notes
    -----
    The function processes functions in a bottom-up order based on their
    dependencies to ensure accurate context generation.
    
    In dry-run mode, the function generates prompt Markdown files without
    calling the LLM.
    
    The function supports both generation of new docstrings and
    verification of existing ones based on the mode parameter.
    """
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
    title_client = None
    if not dry_run:
        client = (
            MistralClient(model=llm_model)
            if active_provider == "mistral"
            else OllamaClient(host=config.llm.host, model=llm_model)
        )
        if title_model:
            title_client = OllamaClient(
                host="http://localhost:11434", model=title_model
            )
    readme_path = Path("README.md")
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        matches = re.findall(
            "<!--\\s*START_CONTEXT\\s*-->(.*?)<!--\\s*END_CONTEXT\\s*-->",
            readme_text,
            re.DOTALL,
        )
        if matches:
            readme_context = "\n\n".join((block.strip() for block in matches))
        else:
            readme_context = readme_text[:2000]
    else:
        readme_context = "No global context available."
    examples_directive = (
        "Include a concise 'Examples' block showing standard usage."
        if examples
        else "Do not include an 'Examples' block unless necessary."
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
                    if (
                        dep_path in known_project_symbols
                        and dep_path != func_logical_path
                    ):
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
    typer.echo(
        f"\nBeginning context-aware docstring injection (Mode: {mode.upper()})..."
    )
    for node_path in execution_order:
        if node_path not in function_registry:
            continue
        target = function_registry[node_path]
        file_path = target["_file_path"]
        has_docstring = bool(target["docstring"])
        if mode == "generate" and has_docstring:
            generated_docstrings_cache[node_path] = target["docstring"]
            continue
        if mode == "verify" and (not has_docstring):
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
        system_prompt = templates.AUTODOC_SYSTEM_PROMPT.format(
            style_guide=templates.NUMPY_STYLE_GUIDE,
            beartype_guide=templates.BEARTYPE_STYLE_GUIDE,
        )
        if mode == "generate":
            user_prompt = templates.AUTODOC_GENERATE_USER.format(
                examples_directive=examples_directive,
                readme_context=readme_context,
                signature=target["signature"],
                code=target["code"],
                dependency_context=dependency_context if dependency_context else "None",
            )
        else:
            user_prompt = templates.AUTODOC_VERIFY_USER.format(
                examples_directive=examples_directive,
                readme_context=readme_context,
                signature=target["signature"],
                code=target["code"],
                existing_docstring=target["docstring"],
            )
        tool_schema = get_autodoc_tool_schema()
        if dry_run:
            dry_dir = Path("dry_run_autodoc_prompts")
            dry_dir.mkdir(exist_ok=True)
            md_path = dry_dir / f"{file_path.stem}_{target['name']}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# System Prompt\n\n```text\n{system_prompt}\n```\n\n")
                f.write(f"# User Prompt\n\n```text\n{user_prompt}\n```\n")
                f.write(f"# JSON Schema\n\n```text\n{str(tool_schema)}\n```\n")
            generated_docstrings_cache[node_path] = (
                target["docstring"]
                if has_docstring
                else f"[DRY RUN: Simulated docstring for {target['name']}]"
            )
            typer.echo(f"     [DRY RUN] Generated prompt -> {md_path}")
            continue
        try:
            raw_response = client.generate_test(
                system_prompt, user_prompt, temperature=0.025, tool_schema=tool_schema
            )
            if verbose:
                typer.secho("\n[DEBUG] --- RAW LLM RESPONSE ---", fg=typer.colors.CYAN)
                typer.secho(raw_response, fg=typer.colors.CYAN)
                typer.secho("[DEBUG] ------------------------\n", fg=typer.colors.CYAN)
            payload_str = raw_response
            match = re.search("\\{.*\\}", raw_response, re.DOTALL)
            if match:
                payload_str = match.group(0)
            payload = json.loads(payload_str)
            if "arguments" in payload:
                payload = payload["arguments"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
            try:
                doc_schema = NumpyDocstringSchema(**payload)
            except Exception as schema_err:
                typer.secho(
                    f"     [ERROR] LLM output failed schema validation: {schema_err}",
                    fg=typer.colors.RED,
                )
                continue
            if title_client and doc_schema.short_summary:
                title_sys_prompt = "You are a strict technical editor. Rewrite the given sentence into a single, imperative sentence (starting with a verb like Compute, Extract, Generate). It MUST be strictly under 70 characters. Output ONLY the raw sentence. Do not include quotes, markdown, or conversational filler. If full meaning cannot be kept only keep the essential."
                title_user_prompt = f"Rewrite this summary to be an imperative command under 70 characters:\n\n{doc_schema.short_summary}"
                if len(doc_schema.short_summary) > 70:
                    n_tries = 4
                    try_i = 1
                    while try_i <= n_tries:
                        try:
                            raw_title = title_client.generate_test(
                                title_sys_prompt,
                                title_user_prompt,
                                temperature=0.0 + 0.05 * (try_i - 1),
                                tool_schema=None,
                            )
                            compressed_title = raw_title.strip("\"`' \n")
                            if 0 < len(compressed_title) <= 75:
                                if verbose:
                                    typer.secho(
                                        f"     [TITLE COMPRESSED] '{doc_schema.short_summary}' -> '{compressed_title}'",
                                        fg=typer.colors.CYAN,
                                    )
                                doc_schema.short_summary = compressed_title.capitalize()
                                break
                            elif try_i <= n_tries:
                                if verbose:
                                    typer.secho(
                                        f"     [TITLE COMPRESSION FAILED] Output was {len(compressed_title)} chars trying again {str(try_i) + '/' + str(n_tries)}.",
                                        fg=typer.colors.YELLOW,
                                    )
                                    try_i += 1
                            if try_i > n_tries:
                                typer.secho(
                                    f"     [TITLE COMPRESSION FAILED] Output was {len(compressed_title)} chars. Keeping original.",
                                    fg=typer.colors.YELLOW,
                                )
                                break
                        except Exception as e:
                            if verbose:
                                typer.secho(
                                    f"     [WARNING] Title compression threw an error: {e}",
                                    fg=typer.colors.YELLOW,
                                )
                                break
            updated_signature = payload.get("updated_signature", "")
            required_imports = payload.get("required_imports", [])
            updated_signature = re.sub(
                "^\\s*```(?:python)?\\n?", "", updated_signature, flags=re.IGNORECASE
            )
            updated_signature = re.sub("\\n?\\s*```\\s*$", "", updated_signature)
            updated_signature = updated_signature.strip("` \n")
            clean_imports = []
            for imp in required_imports:
                imp = re.sub("^\\s*```(?:python)?\\n?", "", imp, flags=re.IGNORECASE)
                imp = re.sub("\\n?\\s*```\\s*$", "", imp)
                imp = imp.strip("` \n")
                if imp:
                    clean_imports.extend(
                        [i.strip() for i in imp.splitlines() if i.strip()]
                    )
            required_imports = clean_imports
            if output_dir:
                out_dir_path = Path(output_dir).resolve()
                rel_path = file_path.relative_to(source_root)
                write_path = out_dir_path / rel_path
                write_path.parent.mkdir(parents=True, exist_ok=True)
                source_code = (
                    write_path.read_text(encoding="utf-8")
                    if write_path.exists()
                    else file_path.read_text(encoding="utf-8")
                )
            else:
                write_path = file_path
                source_code = file_path.read_text(encoding="utf-8")
            base_indent = 4
            for line in source_code.splitlines():
                if re.match(f"^\\s*(async\\s+)?def\\s+{target['name']}\\s*\\(", line):
                    base_indent = len(line) - len(line.lstrip()) + 4
                    break
            new_docstring = build_numpy_docstring(
                doc_schema, base_indent=base_indent, max_line_length=75
            )
            if verbose:
                typer.secho(
                    f"\n[DEBUG] --- INJECTION PAYLOAD FOR {target['name']} ---",
                    fg=typer.colors.MAGENTA,
                )
                typer.secho(
                    f"[DEBUG] updated_signature: {repr(updated_signature)}",
                    fg=typer.colors.MAGENTA,
                )
                typer.secho(
                    f"[DEBUG] required_imports: {repr(required_imports)}",
                    fg=typer.colors.MAGENTA,
                )
                typer.secho(
                    f"[DEBUG] new_docstring (repr): {repr(new_docstring)}",
                    fg=typer.colors.MAGENTA,
                )
                typer.secho(
                    "[DEBUG] --------------------------------------\n",
                    fg=typer.colors.MAGENTA,
                )
            modified_source = inject_autodoc(
                source_code,
                target["name"],
                new_docstring,
                updated_signature,
                required_imports,
            )
            write_path.write_text(modified_source, encoding="utf-8")
            try:
                subprocess.run(
                    [
                        "python",
                        "-m",
                        "ruff",
                        "check",
                        str(write_path),
                        "--fix",
                        "--select",
                        "F401,F811,I",
                    ],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
            generated_docstrings_cache[node_path] = new_docstring
            typer.secho(
                f"     [INJECTED & CLEANED] Successfully wrote to {write_path.name}",
                fg=typer.colors.GREEN,
            )
        except Exception as e:
            typer.secho(
                f"     [ERROR] Failed to inject autodoc: {e}", fg=typer.colors.RED
            )
    typer.echo("\n[SUCCESS] Autodoc pipeline complete.")
