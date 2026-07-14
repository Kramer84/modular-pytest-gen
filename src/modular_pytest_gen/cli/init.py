import sys
from pathlib import Path
from typing import Annotated

import typer

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def init_app(
    force: Annotated[
        bool,
        typer.Option(
            "--force", "-f", help="Overwrite existing autotest.toml if present"
        ),
    ] = False,
):

    config_path = Path("autotest.toml")
    if config_path.exists() and (not force):
        typer.secho(
            "[ERROR] autotest.toml already exists. Use --force to overwrite.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)
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
                typer.echo(
                    f"[INIT] Inferred import_prefix '{import_prefix}' from project name."
                )
            setuptools_where = (
                data.get("tool", {})
                .get("setuptools", {})
                .get("packages", {})
                .get("find", {})
                .get("where", [])
            )
            if setuptools_where and isinstance(setuptools_where, list):
                source_root = setuptools_where[0]
                typer.echo(
                    f"[INIT] Inferred source_root '{source_root}' from setuptools config."
                )
            elif Path("src").exists():
                source_root = "src"
                typer.echo("[INIT] Detected 'src' directory, using as source_root.")
            elif Path(import_prefix).exists():
                source_root = "."
                typer.echo(
                    f"[INIT] Detected flat layout directory '{import_prefix}', using '.' as source_root."
                )
        except Exception as e:
            typer.secho(
                f"[WARN] Failed to parse pyproject.toml for inference: {e}",
                fg=typer.colors.YELLOW,
            )
    template = f'# autotest.toml - Modular Pytest Gen Configuration\n\nsource_root = "{source_root}"\nimport_prefix = "{import_prefix}"\nglobal_context = []\ncustom_instructions = ""\n\n[layout]\nstrategy = "external" \nstructure = "nested"  \ntest_root = "tests"\n\n[discovery]\nrespect_dunder_all = true\ninclude_classes = true\nmax_class_lines = 300\nexclude_patterns = [\n    "*__init__.py",\n    "build",\n    "tests",\n    "*test_*.py"\n]\nexclude_functions = []\n\n[llm]\nprovider = "ollama"\nmodel = "qwen2.5-coder:7b-instruct-q8_0"\nhost = "http://localhost:11434"\nstructured = false\n'
    config_path.write_text(template, encoding="utf-8")
    typer.secho(
        "[SUCCESS] Initialized autotest.toml with inferred defaults.",
        fg=typer.colors.GREEN,
    )
