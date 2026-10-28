import typer
from rich.console import Console

app = typer.Typer(help="perfectmind CLI")
console = Console()


@app.command()
def version() -> None:
    """Print the current version."""
    from perfectmind import __version__

    console.print(__version__)
