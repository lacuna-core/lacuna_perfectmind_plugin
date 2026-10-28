from datetime import date
from urllib.parse import parse_qs

import pytest

from perfectmind.service.swims import (
    SwimService,
    SwimServiceError,
    SwimType,
    classify_swim,
    parse_spots,
)
from tests.conftest import FakeSite, load_fixture

DAY = date(2026, 11, 7)
FIXTURE = "classes_swims_20261107.json"


def requested_programs(site: FakeSite) -> set[str]:
    form = parse_qs(site.classes_requests()[0].content.decode())
    return {form[k][0] for k in form if k.endswith("][Name]")} - {"Date Range"}


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


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Drop-In Lane Swim", "lane"),
        ("Drop-In Endurance Lane Swim", "endurance_lane"),
        ("Drop-in Endurance Lane Swim (25M)", "endurance_lane"),
        ("Drop-In Recreational Swim", "recreational"),
        ("Drop-In Recreational Swim, for ladies", "recreational"),
        ("Drop-In Parent & Tot Swim", None),
        ("Drop-In Therapy Swim", None),
    ],
)
def test_classify_swim(name: str, expected: SwimType | None) -> None:
    assert classify_swim(name) == expected


async def test_list_swims(service: SwimService) -> None:
    sessions = await service.list_swims(DAY)

    assert len(sessions) == 6
    assert [s.start for s in sessions] == sorted(s.start for s in sessions)
    first = sessions[0]
    assert (first.start, first.end) == ("07:00", "08:00")
    assert first.date == DAY
    assert first.swim_type == "lane"
    assert first.location == "Milliken Mills Community Centre"
    assert first.address == "7600 Kennedy Road, Markham, L3R 9S5"
    assert "occurrenceDate=20261107" in first.booking_url
    assert {s.swim_type for s in sessions} == {"lane", "recreational"}
    assert {s.status for s in sessions} == {"open", "full", "not_open"}


async def test_request_includes_all_supported_programs(
    service: SwimService, site: FakeSite
) -> None:
    await service.list_swims(DAY)

    form = parse_qs(site.classes_requests()[0].content.decode())
    assert form["calendarId"] == ["39bd5c76-e07f-43f3-af24-c6969091dbb4"]
    assert form["values[0][Value]"] == ["2026-11-07T00:00:00.000Z"]
    assert requested_programs(site) == {
        "Drop-In Lane Swim",
        "Drop-In Endurance Lane Swim",
        "Drop-In Recreational Swim",
        "Drop-In Recreational Swim, for ladies",
    }


async def test_swim_types_filter(service: SwimService, site: FakeSite) -> None:
    sessions = await service.list_swims(DAY, swim_types=["recreational"])

    assert sessions
    assert all(s.swim_type == "recreational" for s in sessions)
    assert requested_programs(site) == {
        "Drop-In Recreational Swim",
        "Drop-In Recreational Swim, for ladies",
    }


async def test_endurance_lane_only(service: SwimService, site: FakeSite) -> None:
    sessions = await service.list_swims(DAY, swim_types=["endurance_lane"])

    # Fake site ignores filters; the service must still drop non-endurance sessions.
    assert sessions == []
    assert requested_programs(site) == {"Drop-In Endurance Lane Swim"}


async def test_endurance_session_classified(service: SwimService, site: FakeSite) -> None:
    page = load_fixture(FIXTURE)
    page["classes"][0]["EventName"] = "Drop-in Endurance Lane Swim (25M)"
    site.classes_pages = [page]

    sessions = await service.list_swims(DAY)

    assert sessions[0].swim_type == "endurance_lane"


async def test_unclassified_sessions_are_skipped(service: SwimService, site: FakeSite) -> None:
    page = load_fixture(FIXTURE)
    page["classes"][0]["EventName"] = "Drop-In Mystery Swim"
    site.classes_pages = [page]

    assert len(await service.list_swims(DAY)) == 5


async def test_lookups_are_cached(service: SwimService, site: FakeSite) -> None:
    await service.list_swims(DAY)
    await service.list_swims(DAY)

    paths = [r.url.path.rsplit("/", 1)[-1] for r in site.requests]
    assert paths.count("GetCategoriesDataV2") == 1
    assert paths.count("EventFilterGroupsV2") == 1


async def test_follows_next_key_until_day_loaded(service: SwimService, site: FakeSite) -> None:
    page = load_fixture(FIXTURE)
    site.classes_pages = [
        {
            "classes": [{**page["classes"][0], "OccurrenceDate": "20261106"}],
            "nextKey": "2026-11-06",
        },
        page,
    ]

    sessions = await service.list_swims(DAY)

    requests = site.classes_requests()
    assert len(requests) == 2
    assert parse_qs(requests[1].content.decode())["after"] == ["2026-11-06"]
    assert all(s.date == DAY for s in sessions)
    assert len(sessions) == 6


async def test_stops_on_empty_page(service: SwimService, site: FakeSite) -> None:
    site.classes_pages = [{"classes": [], "nextKey": "0001-01-01"}]

    assert await service.list_swims(DAY) == []
    assert len(site.classes_requests()) == 1


async def test_location_filter(service: SwimService) -> None:
    sessions = await service.list_swims(DAY, location="cornell")

    assert {s.swim_type for s in sessions} == {"lane", "recreational"}
    assert all(s.location == "Cornell Community Centre" for s in sessions)


async def test_unknown_location_lists_known_ones(service: SwimService) -> None:
    with pytest.raises(SwimServiceError, match="Cornell Community Centre"):
        await service.list_swims(DAY, location="nowhere")


@pytest.mark.parametrize("day", [date(2026, 10, 27), date(2027, 6, 6)])
async def test_rejects_dates_outside_schedule(service: SwimService, day: date) -> None:
    with pytest.raises(SwimServiceError, match="outside the published schedule"):
        await service.list_swims(day)
