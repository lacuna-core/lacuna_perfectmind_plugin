"""Drop-in swim (lane + recreational) lookups on top of PerfectMindClient."""

import re
import time as _time
from collections.abc import Collection
from datetime import date, datetime
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from perfectmind.client.models import FilterGroup, FilterValue, RawClass
from perfectmind.client.perfectmind import PerfectMindClient

SWIMMING_CALENDAR = "Swimming"

SwimType = Literal["lane", "endurance_lane", "recreational"]
# Matched in order against both Program filter names and event names, e.g. "Drop-In Lane Swim",
# "Drop-in Endurance Lane Swim (25M)", "Drop-In Recreational Swim, for ladies".
# "endurance lane swim" must come before "lane swim", which it contains.
SWIM_TYPE_MARKERS: dict[SwimType, str] = {
    "endurance_lane": "endurance lane swim",
    "lane": "lane swim",
    "recreational": "recreational swim",
}

KIND_PROGRAM = 2
KIND_DATE_RANGE = 6

_FILTER_TTL_SECONDS = 3600
_MAX_PAGES = 5
_NO_NEXT_KEY = "0001-01-01"
_SPOTS_LEFT = re.compile(r"(\d+)\s+spots?\s+left", re.IGNORECASE)

BookingStatus = Literal["open", "full", "not_open"]


class SwimServiceError(Exception):
    """User-facing error (bad date, unknown location, site layout changed)."""


class SwimSession(BaseModel):
    event_id: str
    name: str
    swim_type: SwimType
    date: date
    start: str  # "HH:MM" 24h local time; plain str so JSON schema has no tz-requiring format
    end: str
    duration_min: int | None
    location: str | None
    address: str | None
    facility: str | None
    status: BookingStatus
    spots_left: int | None
    price_range: str | None
    age_restriction: str | None
    booking_url: str


def parse_spots(spots: str | None) -> tuple[BookingStatus, int | None]:
    """'Full' -> full; 'N spots left' -> open; empty -> registration closed or not yet open."""
    text = (spots or "").strip()
    if text.lower() == "full":
        return "full", 0
    if m := _SPOTS_LEFT.search(text):
        return "open", int(m.group(1))
    return "not_open", None


def classify_swim(name: str) -> SwimType | None:
    lowered = name.lower()
    for swim_type, marker in SWIM_TYPE_MARKERS.items():
        if marker in lowered:
            return swim_type
    return None


def _parse_time(value: str) -> str:
    return datetime.strptime(value.strip(), "%I:%M %p").strftime("%H:%M")


def _parse_site_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date()


class SwimService:
    def __init__(self, client: PerfectMindClient) -> None:
        self._client = client
        self._calendar_id: str | None = None
        self._filters: list[FilterGroup] | None = None
        self._filters_at = 0.0

    async def _swimming_calendar_id(self) -> str:
        if self._calendar_id is None:
            for category in await self._client.get_categories():
                for cal in category.calendars:
                    if cal.name.strip().lower() == SWIMMING_CALENDAR.lower():
                        self._calendar_id = cal.id
                        return cal.id
            raise SwimServiceError(f"No '{SWIMMING_CALENDAR}' calendar found in drop-in widget")
        return self._calendar_id

    async def _filter_groups(self) -> list[FilterGroup]:
        # Date-range bounds move daily, so don't cache forever.
        if self._filters is None or _time.monotonic() - self._filters_at > _FILTER_TTL_SECONDS:
            self._filters = await self._client.get_filter_groups(await self._swimming_calendar_id())
            self._filters_at = _time.monotonic()
        return self._filters

    def _group_values(self, groups: list[FilterGroup], kind: int) -> list[FilterValue]:
        return [v for g in groups if g.filter_group_kind == kind for v in g.values]

    async def bookable_range(self) -> tuple[date, date]:
        """Date window the site publishes (first day is the site's 'today')."""
        values = self._group_values(await self._filter_groups(), KIND_DATE_RANGE)
        if not values or not values[0].value or not values[0].value2:
            raise SwimServiceError("Site did not return a date range filter")
        return _parse_site_date(values[0].value), _parse_site_date(values[0].value2)

    async def swim_programs(
        self, swim_types: Collection[SwimType] | None = None
    ) -> list[FilterValue]:
        """Program filter values for the requested swim types (all supported types if empty)."""
        wanted = set(swim_types or SWIM_TYPE_MARKERS)
        programs = [
            v
            for v in self._group_values(await self._filter_groups(), KIND_PROGRAM)
            if classify_swim(v.name) in wanted
        ]
        if not programs:
            kinds = " / ".join(sorted(wanted))
            raise SwimServiceError(f"No {kinds} swim programs found on the Swimming calendar")
        return programs

    async def list_swims(
        self,
        day: date,
        location: str | None = None,
        swim_types: Collection[SwimType] | None = None,
    ) -> list[SwimSession]:
        first, last = await self.bookable_range()
        if not first <= day <= last:
            raise SwimServiceError(
                f"{day.isoformat()} is outside the published schedule "
                f"({first.isoformat()} to {last.isoformat()})"
            )

        iso = f"{day.isoformat()}T00:00:00.000Z"
        filters = [
            FilterValue(name="Date Range", value=iso, value2=iso, value_kind=KIND_DATE_RANGE),
            *await self.swim_programs(swim_types),
        ]
        calendar_id = await self._swimming_calendar_id()
        target = day.strftime("%Y%m%d")

        raw: list[RawClass] = []
        after: str | None = None
        for _ in range(_MAX_PAGES):
            page = await self._client.get_classes(calendar_id, filters, after)
            raw.extend(c for c in page.classes if c.occurrence_date == target)
            # nextKey is the last date loaded; once it reaches `day` the day is complete.
            if not page.classes or not page.next_key or page.next_key == _NO_NEXT_KEY:
                break
            if page.next_key >= day.isoformat():
                break
            after = page.next_key

        sessions: list[SwimSession] = []
        for c in raw:
            kind = classify_swim(c.event_name)
            if kind is None or (swim_types and kind not in swim_types):
                # Server already filtered by program, so this means the site renamed something.
                if kind is None:
                    logger.warning("Skipping unclassified swim session {!r}", c.event_name)
                continue
            sessions.append(self._to_session(c, day, kind))

        what = "swims"
        if swim_types:
            what = " / ".join(t.replace("_", " ") for t in sorted(swim_types)) + " swims"
        if location:
            needle = location.strip().lower()
            matched = [s for s in sessions if s.location and needle in s.location.lower()]
            if not matched and sessions:
                known = sorted({s.location for s in sessions if s.location})
                raise SwimServiceError(
                    f"No {what} at a location matching '{location}' on {day.isoformat()}. "
                    f"Locations with {what} that day: {', '.join(known)}"
                )
            sessions = matched
        return sorted(sessions, key=lambda s: (s.start, s.location or ""))

    def _to_session(self, c: RawClass, day: date, swim_type: SwimType) -> SwimSession:
        status, spots_left = parse_spots(c.spots)
        address = None
        if c.address and c.address.street:
            parts = [c.address.street, c.address.city, c.address.postal_code]
            address = ", ".join(p for p in parts if p)
        return SwimSession(
            event_id=c.event_id,
            name=c.event_name,
            swim_type=swim_type,
            date=day,
            start=_parse_time(c.formatted_start_time),
            end=_parse_time(c.formatted_end_time),
            duration_min=c.duration_in_minutes,
            location=c.location,
            address=address,
            facility=c.facility,
            status=status,
            spots_left=spots_left,
            price_range=c.price_range,
            age_restriction=c.age_restrictions,
            booking_url=self._client.class_url(c.event_id, c.occurrence_date),
        )
