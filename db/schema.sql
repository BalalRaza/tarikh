-- Tarikh database schema
-- Run once against Neon PostgreSQL

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS sources (
    id          SERIAL PRIMARY KEY,
    corpus      TEXT NOT NULL,
    repo        TEXT NOT NULL,
    uri         TEXT NOT NULL UNIQUE,
    meta        JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
    id              TEXT PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    importance      SMALLINT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 3),
    sort_key        INTEGER,
    date_ah         INTEGER,
    date_ce         INTEGER,
    loc_lat         REAL,
    loc_lng         REAL,
    data            JSONB NOT NULL,
    search_vector   tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(data->>'title_en', '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(data->>'title_ar', '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(data->>'summary_en', '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(data->>'summary_ar', '')), 'B')
    ) STORED,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_importance      ON events(importance, sort_key);
CREATE INDEX IF NOT EXISTS idx_events_type_importance ON events(event_type, importance, sort_key);
CREATE INDEX IF NOT EXISTS idx_events_sort_key        ON events(sort_key) WHERE sort_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_date_ah         ON events(date_ah) WHERE date_ah IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_geo             ON events(loc_lat, loc_lng)
                                                      WHERE loc_lat IS NOT NULL AND loc_lng IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_search          ON events USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_events_source          ON events(source_id);
CREATE INDEX IF NOT EXISTS idx_events_people          ON events USING GIN((data->'people') jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_events_title_trgm      ON events USING GIN((data->>'title_en') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_events_title_ar_trgm   ON events USING GIN((data->>'title_ar') gin_trgm_ops);
