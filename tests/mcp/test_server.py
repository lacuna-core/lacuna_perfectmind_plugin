from mcp.client import Client

from perfectmind.mcp.server import build_server
from perfectmind.service.swims import SwimService


async def test_tools_registered(service: SwimService) -> None:
    async with Client(build_server(service)) as client:
        tools = await client.list_tools()

    assert [t.name for t in tools.tools] == ["list_swims"]


async def test_list_swims_tool(service: SwimService) -> None:
    async with Client(build_server(service)) as client:
        result = await client.call_tool(
            "list_swims", {"date": "2026-11-07", "swim_types": ["lane", "endurance_lane"]}
        )

    assert not result.is_error
    assert result.structured_content is not None
    sessions = result.structured_content["result"]
    assert len(sessions) == 3
    assert {s["swim_type"] for s in sessions} == {"lane"}
    assert sessions[0]["start"] == "07:00"
    assert sessions[0]["booking_url"].startswith("https://pm.test/")


async def test_invalid_date_is_tool_error(service: SwimService) -> None:
    async with Client(build_server(service)) as client:
        result = await client.call_tool("list_swims", {"date": "next tuesday"})

    assert result.is_error
    assert "YYYY-MM-DD" in str(result.content)


async def test_output_schema_has_no_time_format(service: SwimService) -> None:
    # Claude Code validates structured output; JSON-schema "time" requires a tz offset.
    async with Client(build_server(service)) as client:
        tools = await client.list_tools()

    assert '"format": "time"' not in str(tools.tools[0].output_schema).replace("'", '"')


async def test_unknown_swim_type_rejected(service: SwimService) -> None:
    async with Client(build_server(service)) as client:
        result = await client.call_tool(
            "list_swims", {"date": "2026-11-07", "swim_types": ["aquafit"]}
        )

    assert result.is_error
