from urllib.parse import parse_qs

from perfectmind.client.models import FilterValue
from perfectmind.client.perfectmind import PerfectMindClient
from tests.conftest import BASE_URL, WIDGET_ID, FakeSite


async def test_get_categories(client: PerfectMindClient, site: FakeSite) -> None:
    categories = await client.get_categories()

    names = [c.name for c in categories[0].calendars]
    assert "Swimming" in names
    assert parse_qs(site.requests[0].content.decode()) == {"widgetId": [WIDGET_ID]}


async def test_get_filter_groups(client: PerfectMindClient, site: FakeSite) -> None:
    groups = await client.get_filter_groups("cal-1")

    assert {g.filter_group_kind for g in groups} >= {2, 6}
    assert site.requests[0].url.params["calendarId"] == "cal-1"


async def test_get_classes_encodes_filters(client: PerfectMindClient, site: FakeSite) -> None:
    filters = [
        FilterValue(name="Date Range", value="2026-11-05T00:00:00.000Z", value2="x", value_kind=6),
        FilterValue(name="Drop-In Lane Swim", value="prog-1", value_kind=2),
    ]

    page = await client.get_classes("cal-1", filters, after="2026-11-04")

    form = parse_qs(site.requests[0].content.decode())
    assert form["calendarId"] == ["cal-1"]
    assert form["after"] == ["2026-11-04"]
    assert form["values[0][ValueKind]"] == ["6"]
    assert form["values[0][Value2]"] == ["x"]
    assert form["values[1][Name]"] == ["Drop-In Lane Swim"]
    assert "values[1][Value2]" not in form
    assert page.next_key == "2026-11-05"
    assert page.classes[0].occurrence_date == "20261105"


def test_class_url(client: PerfectMindClient) -> None:
    url = client.class_url("evt", "20261105")

    assert url.startswith(f"{BASE_URL}/Clients/BookMe4LandingPages/Class?widgetId={WIDGET_ID}")
    assert url.endswith("classId=evt&occurrenceDate=20261105")
