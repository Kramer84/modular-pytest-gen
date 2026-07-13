import typer

from .analyze import analyze_app
from .autodoc import autodoc_app
from .clean import clean_app
from .init import init_app
from .merge import merge_app
from .run import run_app

app = typer.Typer(
    help="Modular Pytest & Doc Gen: AST parsing and LLM prompts.",
    no_args_is_help=True,
    add_completion=True,
)
app.command(name="init", help="Initialize autotest.toml configuration file.")(init_app)
app.command(name="run", help="Generate temporary pytest files via LLM inference.")(
    run_app
)
app.command(
    name="merge", help="Consolidate verified temporary tests into final pytest files."
)(merge_app)
app.command(name="clean", help="Remove temporary files and dry-run prompt artifacts.")(
    clean_app
)
app.command(
    name="analyze", help="Generate a detailed report of successes and failures."
)(analyze_app)
app.command(
    name="autodoc", help="Generate context-aware docstrings using a bottom-up DAG."
)(autodoc_app)


def cli_entry() -> None:
    r"""
    Execute the command-line interface entry point
    
    This function serves as the primary entry point for the command-line
    interface, triggering the application's main execution flow.
    
    Returns
    -------
    None
        This function does not return any value.
    """
    app()



if __name__ == "__main__":
    cli_entry()
