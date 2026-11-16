"""Stage 4: Seed PostgreSQL with processed events."""

import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=5,
        # Keep TCP alive through Neon's idle connection timeout (~5 min).
        server_settings={"keepalives_idle": "60", "keepalives_interval": "10", "keepalives_count": "5"},
    )


async def upsert_source(conn: asyncpg.Connection, uri: str, corpus: str, repo: str, meta: dict) -> int:
    """Insert or get source. Return source_id."""
    row = await conn.fetchrow(
        "INSERT INTO sources (corpus, repo, uri, meta) VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (uri) DO UPDATE SET meta = $4 RETURNING id",
        corpus,
        repo,
        uri,
        json.dumps(meta),
    )
    return row["id"]


async def ensure_source(pool: asyncpg.Pool, uri: str, corpus: str, repo: str, meta: dict) -> int:
    """Upsert source row, return source_id."""
    async with pool.acquire() as conn:
        return await upsert_source(conn, uri, corpus, repo, meta)


async def clear_source_events(pool: asyncpg.Pool, source_id: int) -> None:
    """Delete all events for a source (used for a fresh, non-resumed ingest)."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM events WHERE source_id = $1", source_id)


async def seed_events(pool: asyncpg.Pool, source_id: int, events: list[dict]) -> int:
    """Upsert events for a source (no delete). Returns count upserted.

    Idempotent: event ids are content-derived, so re-seeding overwrites in place.
    Safe to call per batch for crash-resilient incremental ingest.
    """
    if not events:
        return 0
    async with pool.acquire() as conn, conn.transaction():
        # Prepare rows
        rows = []
        for ev in events:
            rows.append(
                (
                    ev["id"],  # id TEXT
                    source_id,  # source_id INTEGER
                    ev["event_type"],  # event_type TEXT
                    ev.get("importance", 3),  # importance SMALLINT
                    ev.get("sort_key"),  # sort_key INTEGER
                    ev.get("date_ah"),  # date_ah INTEGER
                    ev.get("date_ce"),  # date_ce INTEGER
                    ev.get("loc_lat"),  # loc_lat REAL
                    ev.get("loc_lng"),  # loc_lng REAL
                    json.dumps(ev.get("data", ev), ensure_ascii=False),  # data JSONB
                )
            )

        # Bulk insert
        await conn.executemany(
            """INSERT INTO events (id, source_id, event_type, importance, sort_key,
                   date_ah, date_ce, loc_lat, loc_lng, data)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                   ON CONFLICT (id) DO UPDATE SET
                       event_type = EXCLUDED.event_type,
                       importance = EXCLUDED.importance,
                       sort_key = EXCLUDED.sort_key,
                       date_ah = EXCLUDED.date_ah,
                       date_ce = EXCLUDED.date_ce,
                       loc_lat = EXCLUDED.loc_lat,
                       loc_lng = EXCLUDED.loc_lng,
                       data = EXCLUDED.data""",
            rows,
        )
        return len(rows)


async def remove_source(pool: asyncpg.Pool, source_uri: str) -> int:
    """Remove a source and all its events. Returns events deleted."""
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow("SELECT id FROM sources WHERE uri = $1", source_uri)
        if not row:
            return 0
        count = await conn.fetchval("SELECT count(*) FROM events WHERE source_id = $1", row["id"])
        await conn.execute("DELETE FROM sources WHERE id = $1", row["id"])  # CASCADE deletes events
        return count


async def get_status(pool: asyncpg.Pool) -> dict:
    """Get ingestion status: source counts, total events, type breakdown."""
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM events")
        sources = await conn.fetch(
            "SELECT s.uri, s.corpus, count(e.id) as event_count "
            "FROM sources s LEFT JOIN events e ON e.source_id = s.id "
            "GROUP BY s.id ORDER BY s.uri"
        )
        types = await conn.fetch(
            "SELECT event_type, importance, count(*) as cnt "
            "FROM events GROUP BY event_type, importance ORDER BY event_type, importance"
        )
        return {
            "total_events": total,
            "sources": [dict(r) for r in sources],
            "type_breakdown": [dict(r) for r in types],
        }
