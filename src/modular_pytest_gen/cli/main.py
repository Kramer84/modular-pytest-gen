import typer

from .init import init_app
from .run import run_app
from .merge import merge_app

app = typer.Typer(
    help="Modular Pytest & Doc Gen: AST parsing and LLM prompts.",
    no_args_is_help=True,
    add_completion=False,
)
app.command(name="init", help="Initialize autotest.toml configuration file.")(init_app)
app.command(name="run", help="Generate pytest files.")(run_app)
app.command(name="merge", help="Consolidate verified temporary tests into final pytest files.")(merge_app)


def cli_entry():
    """Entry point for the terminal script."""
    app()



if __name__ == "__main__":
    cli_entry()
