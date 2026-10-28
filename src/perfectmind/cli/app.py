import typer
from rich.console import Console

from perfectmind.cli import swims

app = typer.Typer(help="perfectmind CLI")
app.add_typer(swims.app, name="swims")
console = Console()


@app.command()
def version() -> None:
    """Print the current version."""
    from perfectmind import __version__

    console.print(__version__)


@app.command()
def mcp() -> None:
    """Run the PerfectMind MCP server over stdio."""
    from perfectmind.config import SETTINGS
    from perfectmind.mcp.server import run

    run(SETTINGS)
