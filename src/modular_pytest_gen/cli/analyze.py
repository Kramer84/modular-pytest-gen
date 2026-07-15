from pathlib import Path
from typing import Annotated

import typer

from ..analyzer import TestRegistryAnalyzer
from ..config import load_config


def analyze_app(
    config_path: Annotated[
        str, typer.Option("--config", "-c", help="Path to config file")
    ] = "autotest.toml",
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase verbosity (-v for failures, -vv for history)",
        ),
    ] = 0,
):
    r"""
    Analyze the application's test registry.
    
    Parameters
    ----------
    config_path : str, optional
        Path to the configuration file. Default is autotest.toml.
    verbose : int, optional
        Verbosity level. Default is 0.
    
    Raises
    ------
    Exception
        Raised when there is an error loading the configuration file.
    """

    try:
        config = load_config(config_path)
    except Exception as e:
        typer.secho(f"[FATAL] Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    tmp_dir = Path(f"{config.layout.test_root}.tmp")
    typer.echo(f"Scanning test registry at: {tmp_dir}...")
    analyzer = TestRegistryAnalyzer(tmp_dir)
    analyzer.analyze()
    analyzer.print_report(verbosity=verbose)
