-- 001: review gate. Run once after db/schema.sql.
-- Nothing reaches the public timeline unless status = 'approved'.

CREATE TABLE IF NOT EXISTS intakes (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    max_candidates  INTEGER NOT NULL,
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS status     TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('archive', 'pending', 'approved', 'rejected')),
    ADD COLUMN IF NOT EXISTS locked     BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS intake_id  INTEGER REFERENCES intakes(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS passage_ar TEXT,
    ADD COLUMN IF NOT EXISTS grade      CHAR(1) CHECK (grade IN ('A', 'B', 'C', 'D')),
    ADD COLUMN IF NOT EXISTS citations  JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_events_status ON events(status, sort_key);

-- al-Tabari is archive only: never queued for review, never public.
UPDATE events SET status = 'archive'
WHERE source_id IN (SELECT id FROM sources WHERE uri LIKE '0310Tabari.%');
