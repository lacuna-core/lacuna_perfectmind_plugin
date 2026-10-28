import asyncio
from datetime import date
from enum import StrEnum

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Drop-in swim schedules.")
console = Console()


class SwimTypeOption(StrEnum):
    lane = "lane"
    endurance_lane = "endurance_lane"
    recreational = "recreational"


TYPE_LABELS = {"lane": "Lane", "endurance_lane": "Endurance Lane", "recreational": "Recreational"}


@app.command("list")
def list_swims(
    day: str = typer.Option(date.today().isoformat(), "--date", "-d", help="Day as YYYY-MM-DD."),
    location: str | None = typer.Option(None, "--location", "-l", help="Location substring."),
    swim_types: list[SwimTypeOption] | None = typer.Option(
        None, "--type", "-t", help="Swim type to include; repeatable (default: all)."
    ),
) -> None:
    """List drop-in lane, endurance lane and recreational swims for a day."""
    from perfectmind.config import SETTINGS
    from perfectmind.mcp.server import build_http_client
    from perfectmind.service.swims import SwimService, SwimServiceError, SwimSession, SwimType

    async def fetch() -> list[SwimSession]:
        from perfectmind.client.perfectmind import PerfectMindClient

        async with build_http_client(SETTINGS) as http:
            service = SwimService(PerfectMindClient(http, SETTINGS.dropin_widget_id))
            kinds: list[SwimType] = [t.value for t in swim_types or []]
            return await service.list_swims(date.fromisoformat(day), location, kinds)

    try:
        sessions = asyncio.run(fetch())
    except (SwimServiceError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e

    table = Table(title=f"Drop-in swims — {day}")
    for col in ("Time", "Type", "Program", "Location", "Pool", "Status"):
        table.add_column(col)
    for s in sessions:
        status = f"{s.spots_left} left" if s.status == "open" else s.status.replace("_", " ")
        table.add_row(
            f"{s.start}–{s.end}",
            TYPE_LABELS[s.swim_type],
            s.name,
            s.location or "",
            s.facility or "",
            status,
        )
    console.print(table)
