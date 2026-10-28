import asyncio
from datetime import date

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Drop-in swim schedules.")
console = Console()


@app.command()
def lane(
    day: str = typer.Option(date.today().isoformat(), "--date", "-d", help="Day as YYYY-MM-DD."),
    location: str | None = typer.Option(None, "--location", "-l", help="Location substring."),
) -> None:
    """List drop-in lane swims for a day."""
    from perfectmind.config import SETTINGS
    from perfectmind.mcp.server import build_http_client
    from perfectmind.service.swims import SwimService, SwimServiceError, SwimSession

    async def fetch() -> list[SwimSession]:
        from perfectmind.client.perfectmind import PerfectMindClient

        async with build_http_client(SETTINGS) as http:
            service = SwimService(PerfectMindClient(http, SETTINGS.dropin_widget_id))
            return await service.list_lane_swims(date.fromisoformat(day), location)

    try:
        sessions = asyncio.run(fetch())
    except (SwimServiceError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e

    table = Table(title=f"Drop-in lane swims — {day}")
    for col in ("Time", "Program", "Location", "Pool", "Status"):
        table.add_column(col)
    for s in sessions:
        status = f"{s.spots_left} left" if s.status == "open" else s.status.replace("_", " ")
        table.add_row(
            f"{s.start}–{s.end}",
            s.name,
            s.location or "",
            s.facility or "",
            status,
        )
    console.print(table)
