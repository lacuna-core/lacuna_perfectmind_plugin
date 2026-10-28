"""Thin async wrapper over the public (anonymous) PerfectMind BookMe4 JSON endpoints."""

import httpx
from loguru import logger
from pydantic import TypeAdapter

from perfectmind.client.models import Category, ClassesPage, FilterGroup, FilterValue

_CATEGORIES = TypeAdapter(list[Category])
_FILTER_GROUPS = TypeAdapter(list[FilterGroup])


class PerfectMindClient:
    """`http` must have `base_url` set to the tenant root, e.g. https://cityofmarkham.perfectmind.com."""

    def __init__(self, http: httpx.AsyncClient, widget_id: str) -> None:
        self._http = http
        self.widget_id = widget_id

    @property
    def base_url(self) -> str:
        return str(self._http.base_url).rstrip("/")

    async def get_categories(self) -> list[Category]:
        resp = await self._http.post(
            "/Clients/BookMe4V2/GetCategoriesDataV2",
            params={"embed": "False"},
            data={"widgetId": self.widget_id},
        )
        resp.raise_for_status()
        return _CATEGORIES.validate_python(resp.json())

    async def get_filter_groups(self, calendar_id: str) -> list[FilterGroup]:
        resp = await self._http.get(
            "/Clients/BookMe4BookingPagesV2/EventFilterGroupsV2",
            params={"calendarId": calendar_id, "widgetId": self.widget_id},
        )
        resp.raise_for_status()
        return _FILTER_GROUPS.validate_python(resp.json()["filterGroups"])

    async def get_classes(
        self, calendar_id: str, filters: list[FilterValue], after: str | None = None
    ) -> ClassesPage:
        data = {"calendarId": calendar_id, "widgetId": self.widget_id, "page": "0"}
        if after:
            data["after"] = after
        for i, f in enumerate(filters):
            data[f"values[{i}][Name]"] = f.name
            data[f"values[{i}][ValueKind]"] = str(f.value_kind)
            if f.value is not None:
                data[f"values[{i}][Value]"] = f.value
            if f.value2 is not None:
                data[f"values[{i}][Value2]"] = f.value2
        logger.debug("ClassesV2 request: {}", data)
        resp = await self._http.post("/Clients/BookMe4BookingPagesV2/ClassesV2", data=data)
        resp.raise_for_status()
        return ClassesPage.model_validate(resp.json())

    def class_url(self, event_id: str, occurrence_date: str) -> str:
        return (
            f"{self.base_url}/Clients/BookMe4LandingPages/Class?widgetId={self.widget_id}"
            f"&redirectedFromEmbededMode=False&classId={event_id}&occurrenceDate={occurrence_date}"
        )
