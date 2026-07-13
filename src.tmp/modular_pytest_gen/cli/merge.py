from pathlib import Path
from typing import Annotated, Optional

import typer
from typing_extensions import Annotated

from ..config import load_config
from ..layout import LayoutManager
from ..merge import TestMerger


def merge_app(
    config_path: Annotated[str, typer.Option('--config', '-c', help='Path to config file')]='autotest.toml', tmp_dir: Annotated[Optional[str], typer.Option('--tmp-dir', '-t', help='Directory containing temporary test files. Overrides config.')]=None, output_dir: Annotated[Optional[str], typer.Option('--output-dir', '-o', help='Final directory to output merged tests. Overrides config.')]=None):
    r"""
    Merge test files from temporary directory to final output directory.
    
    This function orchestrates the merging of test files from a temporary
    directory to a final output directory. It handles configuration
    loading, directory validation, and the actual merging process.
    
    Parameters
    ----------
    config_path : str, optional (default is 'autotest.toml')
        Path to the configuration file.
    tmp_dir : Optional[str], optional (default is None)
        Directory containing temporary test files. Overrides config if
        provided.
    output_dir : Optional[str], optional (default is None)
        Final directory to output merged tests. Overrides config if
        provided.
    
    Raises
    ------
    typer.Exit : typer.Exit
        - Raised when configuration loading fails.
        - Raised when the temporary directory does not exist or is not a
          directory.
        - Raised when the merge process fails.
    """
    try:
        config = load_config(config_path)
        layout = LayoutManager(config)
    except Exception as e:
        typer.secho(f"[FATAL] Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    active_tmp_dir = tmp_dir if tmp_dir else f"{config.layout.test_root}.tmp"
    active_output_dir = output_dir if output_dir else config.layout.test_root
    typer.echo("Initializing merge sequence...")
    typer.echo(f"  Source (Temp): {active_tmp_dir}")
    typer.echo(f"  Target (Final): {active_output_dir}")
    typer.echo("==============================================")
    tmp_path = Path(active_tmp_dir)
    if not tmp_path.exists() or not tmp_path.is_dir():
        typer.secho(
            f"[ERROR] Temporary directory '{active_tmp_dir}' does not exist or is not a directory.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)
    try:
        merger = TestMerger(
            config=config,
            layout_manager=layout,
            final_test_root=active_output_dir,
            tmp_dir=tmp_path,
        )
        merger.merge_all()
        typer.secho(
            "\n[SUCCESS] Test suite consolidation complete.", fg=typer.colors.GREEN
        )
    except Exception as e:
        typer.secho(f"\n[FATAL] Merge process failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
