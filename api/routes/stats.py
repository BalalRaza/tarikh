from __future__ import annotations
import asyncpg
from fastapi import APIRouter, Depends, Response

from api.db import acquire
from api.models import Stats, TypeCount

router = APIRouter()


@router.get("/stats", response_model=Stats)
async def get_stats(
    response: Response,
    conn: asyncpg.Connection = Depends(acquire),
) -> Stats:
    rows = await conn.fetch(
        "SELECT event_type, importance, COUNT(*) AS count FROM events GROUP BY 1, 2"
    )
    total = sum(r["count"] for r in rows)
    by_type_importance = [
        TypeCount(event_type=r["event_type"], importance=r["importance"], count=r["count"])
        for r in rows
    ]
    return Stats(total=total, by_type_importance=by_type_importance)
