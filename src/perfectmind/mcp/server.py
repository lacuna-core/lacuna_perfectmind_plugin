"""MCP server exposing PerfectMind drop-in swim lookups (stdio transport)."""

from datetime import date

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from perfectmind.config import Settings
from perfectmind.service.swims import SwimService, SwimServiceError, SwimSession, SwimType

INSTRUCTIONS = (
    "Read-only access to the City of Markham PerfectMind booking site. "
    "Currently supports drop-in lane, endurance lane and recreational swims by date."
)


def build_server(service: SwimService) -> MCPServer:
    server = MCPServer("perfectmind", instructions=INSTRUCTIONS)

    @server.tool()
    async def list_swims(
        date: str, location: str | None = None, swim_types: list[SwimType] | None = None
    ) -> list[SwimSession]:
        """List City of Markham drop-in swim sessions (lane, endurance lane, recreational) on a day.

        Args:
            date: Day to look up, ISO format YYYY-MM-DD (resolve "tomorrow" etc. first).
            location: Optional case-insensitive substring of the facility name,
                e.g. "Cornell", "Pan Am", "Milliken".
            swim_types: Optional subset of "lane", "endurance_lane", "recreational";
                omit to get all three.

        Each session has swim_type ("lane", "endurance_lane" or "recreational"), name (the site's program
        name), start/end (HH:MM local Toronto time), location, address, status and a
        booking_url. status: "open" (bookable, see spots_left), "full", or "not_open"
        (registration closed or not yet open; residents can book ~21 hours ahead).
        """
        try:
            day = _parse_date(date)
            return await service.list_swims(day, location, swim_types)
        except SwimServiceError as e:
            raise ToolError(str(e)) from e
        except httpx.HTTPError as e:
            raise ToolError(f"PerfectMind request failed: {e}") from e

    return server


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as e:
        raise SwimServiceError(f"Invalid date '{value}', expected YYYY-MM-DD") from e


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.base_url,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )


def run(settings: Settings) -> None:
    from perfectmind.client.perfectmind import PerfectMindClient

    client = PerfectMindClient(build_http_client(settings), settings.dropin_widget_id)
    build_server(SwimService(client)).run("stdio")
