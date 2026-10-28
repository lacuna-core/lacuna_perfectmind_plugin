import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

from perfectmind.client.perfectmind import PerfectMindClient
from perfectmind.service.swims import SwimService

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://pm.test"
WIDGET_ID = "widget-1"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@dataclass
class FakeSite:
    """Serves recorded PerfectMind responses and records requests."""

    classes_pages: list[Any] = field(
        default_factory=lambda: [load_fixture("classes_swims_20261107.json")]
    )
    requests: list[httpx.Request] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("GetCategoriesDataV2"):
            return httpx.Response(200, json=load_fixture("categories.json"))
        if path.endswith("EventFilterGroupsV2"):
            return httpx.Response(200, json=load_fixture("filter_groups.json"))
        if path.endswith("ClassesV2"):
            calls = sum(1 for r in self.requests if r.url.path.endswith("ClassesV2"))
            pages = self.classes_pages
            page = pages[calls - 1] if calls <= len(pages) else {"classes": [], "nextKey": None}
            return httpx.Response(200, json=page)
        return httpx.Response(404)

    def classes_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path.endswith("ClassesV2")]


@pytest.fixture
def site() -> FakeSite:
    return FakeSite()


@pytest.fixture
async def client(site: FakeSite) -> AsyncIterator[PerfectMindClient]:
    transport = httpx.MockTransport(site.handler)
    async with httpx.AsyncClient(base_url=BASE_URL, transport=transport) as http:
        yield PerfectMindClient(http, WIDGET_ID)


@pytest.fixture
def service(client: PerfectMindClient) -> SwimService:
    return SwimService(client)
