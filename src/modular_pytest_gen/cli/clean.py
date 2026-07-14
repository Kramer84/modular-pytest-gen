import shutil
from pathlib import Path
from typing import Annotated

import typer

from ..config import load_config


def clean_app(
    config_path: Annotated[
        str, typer.Option("--config", "-c", help="Path to config file")
    ] = "autotest.toml",
    dry_run_dir: Annotated[
        str, typer.Option("--dry-run-dir", help="Directory containing dry run prompts")
    ] = "dry_run_prompts",
):

    try:
        config = load_config(config_path)
    except Exception as e:
        typer.secho(f"[FATAL] Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    tmp_dir = Path(f"{config.layout.test_root}.tmp")
    dry_dir = Path(dry_run_dir)
    typer.echo("Initiating workspace cleanup...")
    cleaned_something = False
    if tmp_dir.exists() and tmp_dir.is_dir():
        typer.echo(f"  -> Removing temporary test registry: {tmp_dir}")
        shutil.rmtree(tmp_dir)
        cleaned_something = True
    if dry_dir.exists() and dry_dir.is_dir():
        typer.echo(f"  -> Removing dry run prompts: {dry_dir}")
        shutil.rmtree(dry_dir)
        cleaned_something = True
    if cleaned_something:
        typer.secho("\n[SUCCESS] Workspace cleaned.", fg=typer.colors.GREEN)
    else:
        typer.echo("\n[INFO] Workspace is already clean. Nothing to remove.")
