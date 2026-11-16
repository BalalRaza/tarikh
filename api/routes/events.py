from __future__ import annotations
from typing import Annotated
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.db import acquire
from api.models import EventDetail, EventList, EventSummary, MapMarker, MapResponse

router = APIRouter()


def _row_to_summary(row: asyncpg.Record) -> EventSummary:
    data = row["data"] or {}
    return EventSummary(
        id=row["id"],
        event_type=row["event_type"],
        importance=row["importance"],
        date_ah=row["date_ah"],
        date_ce=row["date_ce"],
        sort_key=row["sort_key"],
        title_en=data.get("title_en"),
        title_ar=data.get("title_ar"),
        summary_en=data.get("summary_en"),
        loc_lat=row["loc_lat"],
        loc_lng=row["loc_lng"],
    )


@router.get("/events/map", response_model=MapResponse)
async def get_map(
    response: Response,
    conn: asyncpg.Connection = Depends(acquire),
) -> MapResponse:
    rows = await conn.fetch(
        """
        SELECT id, event_type, importance, loc_lat, loc_lng, data->>'title_en' AS title_en
        FROM events
        WHERE loc_lat IS NOT NULL AND loc_lng IS NOT NULL
        """
    )
    response.headers["Cache-Control"] = "public, max-age=3600"
    markers = [
        MapMarker(
            id=r["id"],
            title_en=r["title_en"],
            type=r["event_type"],
            importance=r["importance"],
            lat=r["loc_lat"],
            lng=r["loc_lng"],
        )
        for r in rows
    ]
    return MapResponse(markers=markers)


@router.get("/events", response_model=EventList)
async def list_events(
    response: Response,
    conn: asyncpg.Connection = Depends(acquire),
    importance: str | None = Query(None, description="CSV e.g. '1,2'"),
    type: str | None = Query(None, description="CSV e.g. 'battle,political'"),
    q: str | None = Query(None, description="Full-text search"),
    source: str | None = Query(None, description="Source URI prefix, trailing * as LIKE"),
    date_from: int | None = Query(None),
    date_to: int | None = Query(None),
    has_location: bool | None = Query(None),
    cursor: str | None = Query(None, description="'<sort_key>:<id>'"),
    limit: int = Query(200, ge=1, le=500),
) -> EventList:
    conditions: list[str] = []
    args: list = []

    def add(cond: str, *vals) -> None:
        for v in vals:
            args.append(v)
        conditions.append(cond)

    if importance:
        imp_vals = [int(x.strip()) for x in importance.split(",")]
        placeholders = ", ".join(f"${len(args) + i + 1}" for i in range(len(imp_vals)))
        for v in imp_vals:
            args.append(v)
        conditions.append(f"importance IN ({placeholders})")

    if type:
        type_vals = [x.strip() for x in type.split(",")]
        placeholders = ", ".join(f"${len(args) + i + 1}" for i in range(len(type_vals)))
        for v in type_vals:
            args.append(v)
        conditions.append(f"event_type IN ({placeholders})")

    if q:
        args.append(q)
        conditions.append(f"search_vector @@ websearch_to_tsquery('simple', ${len(args)})")

    if source:
        if source.endswith("*"):
            args.append(source[:-1] + "%")
            conditions.append(
                f"source_id IN (SELECT id FROM sources WHERE uri LIKE ${len(args)})"
            )
        else:
            args.append(source)
            conditions.append(
                f"source_id IN (SELECT id FROM sources WHERE uri = ${len(args)})"
            )

    if date_from is not None:
        args.append(date_from)
        conditions.append(f"date_ce >= ${len(args)}")

    if date_to is not None:
        args.append(date_to)
        conditions.append(f"date_ce <= ${len(args)}")

    if has_location is True:
        conditions.append("loc_lat IS NOT NULL")
    elif has_location is False:
        conditions.append("loc_lat IS NULL")

    # Filter args only (count must not include cursor params)
    count_args = list(args)

    # Cursor: (sort_key, id) > (cursor_sk, cursor_id)
    cursor_condition = ""
    if cursor:
        parts = cursor.split(":", 1)
        if len(parts) == 2:
            cursor_sk, cursor_id = int(parts[0]), parts[1]
            args.append(cursor_sk)
            args.append(cursor_id)
            cursor_condition = f"AND (sort_key, id) > (${len(args) - 1}, ${len(args)})"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total count (no cursor)
    count_sql = f"SELECT COUNT(*) FROM events {where}"
    total = await conn.fetchval(count_sql, *count_args)

    # Fetch rows
    data_sql = f"""
        SELECT id, event_type, importance, sort_key, date_ah, date_ce,
               loc_lat, loc_lng, data
        FROM events
        {where}
        {cursor_condition}
        ORDER BY sort_key, id
        LIMIT ${len(args) + 1}
    """
    args.append(limit + 1)
    rows = await conn.fetch(data_sql, *args)

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = f"{last['sort_key']}:{last['id']}"

    response.headers["Cache-Control"] = "public, max-age=3600"
    return EventList(
        events=[_row_to_summary(r) for r in rows],
        next_cursor=next_cursor,
        total=total,
    )


@router.get("/events/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: str,
    response: Response,
    conn: asyncpg.Connection = Depends(acquire),
) -> EventDetail:
    row = await conn.fetchrow(
        """
        SELECT e.id, e.event_type, e.importance, e.sort_key, e.date_ah, e.date_ce,
               e.loc_lat, e.loc_lng, e.data,
               s.corpus, s.repo, s.uri, s.meta
        FROM events e
        JOIN sources s ON s.id = e.source_id
        WHERE e.id = $1
        """,
        event_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")

    response.headers["Cache-Control"] = "public, max-age=86400"
    return EventDetail(
        id=row["id"],
        event_type=row["event_type"],
        importance=row["importance"],
        sort_key=row["sort_key"],
        date_ah=row["date_ah"],
        date_ce=row["date_ce"],
        loc_lat=row["loc_lat"],
        loc_lng=row["loc_lng"],
        data=dict(row["data"]),
        source={
            "corpus": row["corpus"],
            "repo": row["repo"],
            "uri": row["uri"],
            "meta": dict(row["meta"]) if row["meta"] else {},
        },
    )
