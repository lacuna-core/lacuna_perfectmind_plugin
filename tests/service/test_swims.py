from datetime import date
from urllib.parse import parse_qs

import pytest

from perfectmind.service.swims import SwimService, SwimServiceError, parse_spots
from tests.conftest import FakeSite, load_fixture

DAY = date(2026, 11, 5)


@pytest.mark.parametrize(
    ("spots", "expected"),
    [
        ("Full", ("full", 0)),
        ("12 spots left", ("open", 12)),
        ("1 spot left", ("open", 1)),
        ("", ("not_open", None)),
        (None, ("not_open", None)),
    ],
)
def test_parse_spots(spots: str | None, expected: tuple[str, int | None]) -> None:
    assert parse_spots(spots) == expected


async def test_list_lane_swims(service: SwimService, site: FakeSite) -> None:
    sessions = await service.list_lane_swims(DAY)

    assert len(sessions) == 6
    assert sessions == sorted(sessions, key=lambda s: (s.start, s.location or ""))
    first = sessions[0]
    assert first.start == "07:00"
    assert first.end == "08:00"
    assert first.date == DAY
    assert first.location == "Milliken Mills Community Centre"
    assert first.address == "7600 Kennedy Road, Markham, L3R 9S5"
    assert "occurrenceDate=20261105" in first.booking_url
    assert {s.status for s in sessions} == {"open", "full", "not_open"}


async def test_request_uses_date_and_lane_program_filters(
    service: SwimService, site: FakeSite
) -> None:
    await service.list_lane_swims(DAY)

    form = parse_qs(site.classes_requests()[0].content.decode())
    assert form["calendarId"] == ["39bd5c76-e07f-43f3-af24-c6969091dbb4"]
    assert form["values[0][Value]"] == ["2026-11-05T00:00:00.000Z"]
    programs = {form[k][0] for k in form if k.endswith("][Name]")} - {"Date Range"}
    assert programs == {"Drop-In Lane Swim", "Drop-In Endurance Lane Swim"}


async def test_lookups_are_cached(service: SwimService, site: FakeSite) -> None:
    await service.list_lane_swims(DAY)
    await service.list_lane_swims(DAY)

    paths = [r.url.path.rsplit("/", 1)[-1] for r in site.requests]
    assert paths.count("GetCategoriesDataV2") == 1
    assert paths.count("EventFilterGroupsV2") == 1


async def test_follows_next_key_until_day_loaded(service: SwimService, site: FakeSite) -> None:
    page = load_fixture("classes_lane_20261105.json")
    site.classes_pages = [
        {
            "classes": [{**page["classes"][0], "OccurrenceDate": "20261104"}],
            "nextKey": "2026-11-04",
        },
        page,
    ]

    sessions = await service.list_lane_swims(DAY)

    requests = site.classes_requests()
    assert len(requests) == 2
    assert parse_qs(requests[1].content.decode())["after"] == ["2026-11-04"]
    assert all(s.date == DAY for s in sessions)
    assert len(sessions) == 6


async def test_stops_on_empty_page(service: SwimService, site: FakeSite) -> None:
    site.classes_pages = [{"classes": [], "nextKey": "0001-01-01"}]

    assert await service.list_lane_swims(DAY) == []
    assert len(site.classes_requests()) == 1


async def test_location_filter(service: SwimService) -> None:
    sessions = await service.list_lane_swims(DAY, location="cornell")

    assert sessions
    assert all(s.location == "Cornell Community Centre" for s in sessions)


async def test_unknown_location_lists_known_ones(service: SwimService) -> None:
    with pytest.raises(SwimServiceError, match="Cornell Community Centre"):
        await service.list_lane_swims(DAY, location="nowhere")


@pytest.mark.parametrize("day", [date(2026, 10, 27), date(2027, 6, 6)])
async def test_rejects_dates_outside_schedule(service: SwimService, day: date) -> None:
    with pytest.raises(SwimServiceError, match="outside the published schedule"):
        await service.list_lane_swims(day)
