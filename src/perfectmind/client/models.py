"""Raw PerfectMind BookMe4 payloads. Field names mirror the site's PascalCase JSON."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_pascal


class PascalModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_pascal, populate_by_name=True, extra="ignore")


class Calendar(PascalModel):
    id: str
    name: str


class Category(PascalModel):
    name: str
    calendars: list[Calendar] = []


class FilterValue(PascalModel):
    name: str
    value: str | None = None
    value2: str | None = None
    value_kind: int


class FilterGroup(PascalModel):
    filter_group_kind: int
    values: list[FilterValue] = []


class Address(PascalModel):
    street: str | None = None
    city: str | None = None
    postal_code: str | None = None


class RawClass(PascalModel):
    event_id: str
    event_name: str
    occurrence_date: str  # yyyyMMdd
    formatted_start_time: str  # "08:00 PM"
    formatted_end_time: str
    duration_in_minutes: int | None = None
    location: str | None = None
    address: Address | None = None
    facility: str | None = None
    spots: str | None = None  # "Full" | "N spots left" | ""
    price_range: str | None = None
    age_restrictions: str | None = None
    book_button_text: str | None = None


class ClassesPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    classes: list[RawClass] = []
    next_key: str | None = Field(default=None, alias="nextKey")
