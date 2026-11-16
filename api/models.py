from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class EventSummary(BaseModel):
    id: str
    event_type: str
    importance: int
    date_ah: int | None
    date_ce: int | None
    sort_key: int | None
    title_en: str | None
    title_ar: str | None
    summary_en: str | None
    loc_lat: float | None
    loc_lng: float | None


class EventDetail(BaseModel):
    id: str
    event_type: str
    importance: int
    date_ah: int | None
    date_ce: int | None
    sort_key: int | None
    loc_lat: float | None
    loc_lng: float | None
    data: dict[str, Any]
    source: dict[str, Any]


class EventList(BaseModel):
    events: list[EventSummary]
    next_cursor: str | None
    total: int


class MapMarker(BaseModel):
    id: str
    title_en: str | None
    type: str
    importance: int
    lat: float
    lng: float


class MapResponse(BaseModel):
    markers: list[MapMarker]


class TypeCount(BaseModel):
    event_type: str
    importance: int
    count: int


class Stats(BaseModel):
    total: int
    by_type_importance: list[TypeCount]
