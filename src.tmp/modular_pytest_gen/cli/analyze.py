from pathlib import Path

import typer

from ..analyzer import TestRegistryAnalyzer
from ..config import load_config


def analyze_app(
    config_path: str = 'autotest.toml', verbose: int = 0):
    r"""
    Analyze the test registry using configuration settings.
    
    This function loads configuration settings, initializes a test registry
    analyzer, and generates a detailed report of the test registry's
    status.
    
    Parameters
    ----------
    config_path : str, optional (default is 'autotest.toml')
        Path to the configuration file.
    verbose : int, optional (default is 0)
        Verbosity level for the report.
    
    Raises
    ------
    typer.Exit : typer.Exit
        Configuration file loading failure.
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
