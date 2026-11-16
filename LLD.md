# Tarikh — Low-Level Design Document

**Scale**: 500K–5M events. Multiple sources (OpenITI repos, 0025AH–1500AH+), added/removed over time. Read-heavy, batch-write ingestion.

**Running cost**: $0/mo at MVP. $27/mo fully scaled.

**Ingestion cost**: $0 (Google AI Studio free tier + hybrid pipeline).

---

## 1. System Overview

```
                              ┌───────────────────────────┐
                              │    Ingestion Pipeline     │
                              │    (offline, batch)       │
                              │                           │
                              │  Stage 1: Rules (free)    │
                              │  Stage 2: NLP (free)      │
                              │  Stage 3: LLM (free tier) │
                              │  Stage 4: Seed DB         │
                              └─────────────┬─────────────┘
                                            │ bulk insert
                                            ▼
┌──────────────────┐  REST  ┌──────────────┐    ┌────────────────────┐
│    Frontend      │───────▶│  API Server  │───▶│    PostgreSQL      │
│    Vite + TS     │◀───────│  FastAPI     │◀───│    (Neon free)     │
│    GSAP / Three  │        │  Python      │    │    JSONB + indexes │
└──────────────────┘        └──────────────┘    └────────────────────┘
        │                          │
   Cloudflare Pages         Render Web Service
   (free, global CDN)          (free tier)
```

---

## 2. Database

### 2.1 PostgreSQL + JSONB (via Neon)

At 500K–5M events, SQLite can't scale (multi-GB file, no Arabic FTS, Render's disk is ephemeral). Pure NoSQL (MongoDB, DynamoDB) loses `pg_trgm` Arabic search and costs more — Atlas Search is a paid add-on, DynamoDB requires GSI capacity planning.

**Hybrid approach**: promote only the fields you *query on* to indexed columns. Everything else lives in a `data JSONB` column — the source of truth. Schema changes = new keys in the JSON blob, zero migrations.

**Neon** (serverless PostgreSQL): free tier = 512MB, 100 compute-hours/mo, auto-suspend. At ~1KB/event, 512MB holds ~500K events. Scale to $19/mo (10GB) when needed. Built-in connection pooler.

### 2.2 Schema

```sql
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    corpus      TEXT NOT NULL,
    repo        TEXT NOT NULL,
    uri         TEXT NOT NULL UNIQUE,
    meta        JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE events (
    -- Indexed query columns (promoted from JSONB)
    id              TEXT PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    event_type      TEXT NOT NULL,
    importance      SMALLINT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 3),
    sort_key        INTEGER,
    date_ah         INTEGER,
    date_ce         INTEGER,
    loc_lat         REAL,
    loc_lng         REAL,

    -- Full event document (source of truth)
    data            JSONB NOT NULL,

    -- Generated search column
    search_vector   tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(data->>'title_en', '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(data->>'title_ar', '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(data->>'summary_en', '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(data->>'summary_ar', '')), 'B')
    ) STORED,

    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_events_importance       ON events(importance, sort_key);
CREATE INDEX idx_events_type_importance  ON events(event_type, importance, sort_key);
CREATE INDEX idx_events_sort_key         ON events(sort_key) WHERE sort_key IS NOT NULL;
CREATE INDEX idx_events_date_ah          ON events(date_ah) WHERE date_ah IS NOT NULL;
CREATE INDEX idx_events_geo              ON events(loc_lat, loc_lng)
                                         WHERE loc_lat IS NOT NULL AND loc_lng IS NOT NULL;
CREATE INDEX idx_events_search           ON events USING GIN(search_vector);
CREATE INDEX idx_events_source           ON events(source_id);
CREATE INDEX idx_events_people           ON events USING GIN((data->'people') jsonb_path_ops);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_events_title_trgm       ON events USING GIN((data->>'title_en') gin_trgm_ops);
CREATE INDEX idx_events_title_ar_trgm    ON events USING GIN((data->>'title_ar') gin_trgm_ops);
```

### 2.3 Query Patterns

```sql
-- Primary use case: all importance=1 events
SELECT id, event_type, importance, sort_key, date_ah, date_ce,
       data->>'title_en' AS title_en, data->>'title_ar' AS title_ar,
       data->'location'->>'name_en' AS loc_name
FROM events WHERE importance = 1 ORDER BY sort_key LIMIT 200;

-- Cursor-based pagination (O(1) at any depth)
SELECT id, event_type, importance, sort_key, data->>'title_en' AS title_en
FROM events
WHERE importance <= 2 AND (sort_key, id) > ($cursor_sort_key, $cursor_id)
ORDER BY sort_key, id LIMIT 200;

-- FTS search (Arabic + English)
SELECT id, importance, sort_key, data->>'title_en' AS title_en,
       ts_rank(search_vector, query) AS rank
FROM events, plainto_tsquery('simple', $q) query
WHERE search_vector @@ query ORDER BY rank DESC LIMIT 50;

-- Event detail — return full document
SELECT data FROM events WHERE id = $id;

-- Map markers — lightweight projection
SELECT id, event_type, importance, loc_lat, loc_lng, date_ce,
       data->>'title_en' AS title_en
FROM events WHERE loc_lat IS NOT NULL AND importance <= $max_importance;

-- Person lookup
SELECT id, data->>'title_en' AS title_en, sort_key
FROM events WHERE data->'people' @> '[{"name_en": "Umar ibn al-Khattab"}]';

-- Re-ingest a source
DELETE FROM events WHERE source_id = (SELECT id FROM sources WHERE uri = $uri);

-- Stats
SELECT event_type, importance, count(*) FROM events GROUP BY 1, 2;
```

### 2.4 Schema Evolution Rules

1. **New field from extractor** → lands in `data` JSONB. No migration.
2. **Need to filter/sort on a new field** → `ALTER TABLE ADD COLUMN` + `CREATE INDEX` + backfill from `data`.
3. **New event type** → just a new string value (TEXT, not ENUM).
4. **New source format** → new parser in `pipeline/parsers/`, same output shape.

### 2.5 Event Type Normalization

Collapse POC's 16 types into 10 canonical types during seeding:

| Canonical       | Absorbs                                       |
|-----------------|-----------------------------------------------|
| `battle`        | `battle`, `military`, `military_mobilization` |
| `political`     | `political`, `diplomatic`                     |
| `death`         | `death`                                       |
| `birth`         | `birth`                                       |
| `migration`     | `migration`                                   |
| `revelation`    | `revelation`, `miraculous`, `religious`        |
| `treaty`        | `treaty`                                      |
| `social`        | `social`, `conversion`                        |
| `construction`  | `construction`                                |
| `other`         | anything unmapped                             |

### 2.6 Future: Person Entity Resolution

At 5M events × 2.7 people/event = ~13.5M person mentions. Many duplicates. When person-centric features are needed (biography pages, relationship graphs):

```sql
CREATE TABLE people (
    id      SERIAL PRIMARY KEY,
    name_en TEXT NOT NULL UNIQUE,
    name_ar TEXT
);
-- event_people.person_id FK → people.id
```

---

## 3. Backend API

### 3.1 Stack

| Component | Choice |
|-----------|--------|
| Framework | FastAPI (async, auto OpenAPI docs) |
| DB driver | asyncpg |
| Validation | Pydantic v2 |
| Serialization | orjson |

### 3.2 Endpoints

```
GET  /api/v1/events
     ?importance=1,2
     &type=battle,political
     &q=khadijah
     &source=0310Tabari*
     &date_from=-600&date_to=700
     &has_location=true
     &cursor=<sort_key>:<id>
     &limit=200
     → { events: [...], next_cursor, total }

GET  /api/v1/events/:id         → full event + source detail
GET  /api/v1/events/map         → { markers: [{ id, title_en, type, importance, lat, lng }] }
GET  /api/v1/stats              → counts by type × importance, date histogram
GET  /api/v1/types              → event types with counts
GET  /api/v1/sources            → ingested sources with event counts
GET  /api/v1/people?q=umar     → person search across events
```

### 3.3 Cursor-Based Pagination

Offset pagination scans O(n) rows at 5M scale. Cursor uses compound key `(sort_key, id)`:

```python
cursor = f"{event.sort_key}:{event.id}"
# WHERE (sort_key, id) > ($sort_key, $id) ORDER BY sort_key, id LIMIT $n
```

O(1) at any depth.

### 3.4 Caching

| Resource | Strategy | TTL |
|----------|----------|-----|
| Stats | In-memory, computed at startup | Until restart |
| Event lists | `Cache-Control: public, max-age=3600` | 1 hour |
| Event detail | `Cache-Control: public, max-age=86400` | 1 day |
| Map markers | `Cache-Control: public, max-age=3600` | 1 hour |

Data changes only on re-ingestion. Aggressive caching is safe.

---

## 4. Frontend

### 4.1 Stack

| Layer          | Choice                        | Why                                    |
|----------------|-------------------------------|----------------------------------------|
| Build          | Vite                          | Fast, no framework lock-in             |
| Language       | TypeScript                    | Type safety                            |
| Routing        | Barba.js                      | Page transitions without SPA framework |
| Animations     | GSAP + ScrollTrigger          | Awwwards standard                      |
| Smooth scroll  | Lenis                         | Buttery native-feel scroll             |
| Text animation | SplitType                     | Char/word/line splitting for reveals   |
| 3D             | Three.js                      | Globe, WebGL backgrounds               |
| Maps           | MapLibre GL JS                | Free, no API key (Carto dark tiles)    |
| Map clustering | supercluster                  | Client-side clustering for 100K+ pts   |
| Timeline       | Custom Canvas renderer        | Full design control, handles 100K+     |
| Typography     | Amiri (Arabic), Inter (Latin) | Variable weight, elegant               |
| Icons          | Phosphor                      | Clean, consistent                      |

### 4.2 Rendering at Scale

The frontend never loads all events. Server does the filtering.

**Timeline**: Canvas-rendered. LOD: zoomed out = importance=1 dots only; zoomed in = all events with labels. Fetches from API as viewport changes (debounced). Era bands as background color zones.

**Map**: `/api/v1/events/map` returns lightweight markers. Client-side `supercluster` handles clustering. At zoom 1 → ~50 clusters. At zoom 15 → individual markers.

**List/search**: Cursor-paginated. Infinite scroll with IntersectionObserver. 200 events per page.

### 4.3 Pages

```
/                   → Hero with globe + era overview
/timeline           → Interactive timeline (core view)
/map                → Geographic exploration
/event/:id          → Event detail (deep-linkable)
/source/:uri        → Events from a source text
/about              → Project info, methodology
```

### 4.4 Components

1. **Hero** — Full-viewport. Rotating Three.js globe with importance=1 markers. Arabic calligraphy title (SplitType + GSAP). Scroll cue.
2. **Timeline** — Canvas horizontal timeline. Era bands. Zoom-driven importance filtering.
3. **Event Card** — Glassmorphism, type-colored accent. Hover: scale + glow.
4. **Map View** — MapLibre + Carto Dark Matter tiles. Supercluster. Color-coded by type.
5. **Detail View** — Arabic text in Amiri RTL. Source citation. People chips. Related events.
6. **Filters** — Importance toggle, type chips, date range slider, search. Persisted in URL params.

### 4.5 Animation Budget

| Trigger | Animation |
|---------|-----------|
| Page load | Staggered reveal: header → hero text → globe |
| Scroll | Parallax layers, ScrollTrigger section reveals |
| Navigation | Barba.js cross-fade/slide transitions |
| Hover | Scale, glow, cursor follow |
| Timeline zoom | GSAP interpolation, events fade by importance |
| Filters | FLIP technique for item reflow |
| Cursor | Custom dot + ring, context-aware |
| Loading | Skeleton shimmer |

### 4.6 Design-First Workflow

**Figma** (free plan):

1. Design system: colors, typography scale, spacing, component library
2. Desktop layouts: Home, Timeline, Map, Event Detail, Source
3. Tablet + mobile responsive
4. Animation specs (duration, easing, triggers)
5. Export tokens → `design/tokens.json`
6. Implement in code

Palette: dark navy (#0A1628), gold (#D4A853), warm white (#F5F0E8), type accent colors from POC.

---

## 5. Ingestion Pipeline

### 5.1 The Cost Problem

The POC sends every section to Gemini and asks it to do everything: dates, people, types, translation, summarization, importance, geocoding. Most of this doesn't need an LLM.

| Task | Needs LLM? | Free alternative |
|------|-----------|-----------------|
| Date extraction | No | Regex on headers — "ثم دخلت سنة ثلاث عشرة" → 13 AH |
| AH→CE conversion | No | Math (existing `ah_to_ce()`) |
| Event type classification | No | Keyword match — غزوة→battle, وفاة→death, بيعة→political |
| People extraction | Mostly no | CAMeL Tools Arabic NER (free, local) |
| Location extraction | Mostly no | CAMeL Tools NER + gazetteer |
| Geocoding | No | al-Thurayya gazetteer (~2K historical places with coords) |
| Translation | Depends | argos-translate (free, local) or Google Translate free tier |
| Event boundaries | No | Already defined by mARkdown headers |
| Summarization | Yes | Cheapest LLM |
| Importance scoring | Partially | Rules for 1 vs 3; LLM for edge cases |
| Confidence assessment | No | Drop it — low value, high cost |

**~70% is rule-based or free NLP.** The LLM handles only summarization and importance.

### 5.2 Hybrid Pipeline

```
Source text (mARkdown)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1: Rules (FREE, local)                       │
│                                                     │
│  parser.py         → sections                       │
│  date_extractor.py → date_ah (regex on headers)     │
│  type_classifier.py → event_type (keyword match)    │
│  ah_to_ce()        → date_ce, sort_key              │
│                                                     │
│  Cost: $0                                           │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  Stage 2: NLP (FREE, local)                         │
│                                                     │
│  CAMeL Tools NER  → person names, location names    │
│  Gazetteer lookup → lat/lng                         │
│  argos-translate  → title_en (rough)                │
│                                                     │
│  Cost: $0 (CPU, ~2s/section)                        │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  Stage 3: LLM (FREE tier)                           │
│                                                     │
│  Input:  section text + pre-extracted fields        │
│  Output: summary_ar, summary_en, importance,        │
│          refined title_en                           │
│                                                     │
│  Model: Gemini 3.1 Flash-Lite + 2.5 Flash-Lite     │
│  via Google AI Studio FREE Standard tier            │
│                                                     │
│  Cost: $0 (rate-limited, not price-limited)         │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  Stage 4: Seed DB                                   │
│                                                     │
│  Merge all outputs → normalize types → dedup        │
│  → bulk INSERT into PostgreSQL                      │
│                                                     │
│  Cost: $0                                           │
└─────────────────────────────────────────────────────┘
```

### 5.3 LLM Cost: $0

Google AI Studio free tier (ai.google.dev/pricing, verified June 2026):

| Model | Free Standard | Paid Standard (/1M) | Paid Batch (/1M) |
|-------|--------------|--------------------|--------------------|
| **Gemini 3.1 Flash-Lite** | **$0 in, $0 out** | $0.25 in, $1.50 out | $0.125 in, $0.75 out |
| **Gemini 2.5 Flash-Lite** | **$0 in, $0 out** | $0.10 in, $0.40 out | $0.05 in, $0.20 out |

Free tier rate limits: ~1,000 RPD, 30 RPM per model.

**Note**: Gemini 2.0 Flash-Lite was shut down June 1, 2026. Use 2.5 or 3.1 instead. The POC's `extractor.py` must update the model name.

**Throughput calculation for 5M events (~2M sections):**

- Batch 10 sections per request → 200K requests
- 2 models in parallel → 2,000 RPD effective
- 200K / 2,000 = **100 days (~3.3 months)**
- Total LLM cost: **$0**

Caveat: free tier data used to improve Google's products. Source texts are public domain (OpenITI). Acceptable.

### 5.4 Cost Comparison (5M events)

| Approach | LLM Cost | Quality | Time |
|----------|---------|---------|------|
| POC (all Gemini 2.5 Flash, paid) | ~$1,500+ | Best | ~7 days |
| **Hybrid + free tier (2 models)** | **$0** | **90%+** | **~3.3 months** |
| Hybrid + local Qwen3-8B | $0 | 85–90% | ~5 days |
| Hybrid + paid Batch API | ~$175 | 90%+ | ~2 days |
| Rules + NLP only (no LLM) | $0 | Partial | ~1 day |

**Recommended**: Hybrid + Google AI Studio free tier. $0, 90%+, ~3.3 months. Use local Qwen3-8B for dev/testing.

### 5.5 Rule-Based Extractors

**Arabic numeral parser** (covers 100% of al-Tabari's 346 year headers):

```python
ARABIC_NUMBERS = {
    'إحدى': 1, 'اثنتي': 2, 'ثلاث': 3, 'أربع': 4, 'خمس': 5,
    'ست': 6, 'سبع': 7, 'ثمان': 8, 'تسع': 9, 'عشر': 10,
    'عشرة': 10, 'عشرين': 20, 'ثلاثين': 30, 'أربعين': 40,
    'خمسين': 50, 'ستين': 60, 'سبعين': 70, 'ثمانين': 80,
    'تسعين': 90, 'مئة': 100, 'مائة': 100, 'مائتين': 200,
    'ثلاثمائة': 300,  # ...
}
# "سنة ثلاث عشرة" → 13
# "سنة إحدى وعشرين" → 21
```

**Event type keywords** (match against headers, then body):

```python
TYPE_KEYWORDS = {
    'battle':       ['غزوة', 'غزو', 'وقعة', 'معركة', 'فتح', 'حرب', 'سرية', 'حصار'],
    'death':        ['وفاة', 'موت', 'مقتل', 'قتل', 'هلاك', 'استشهاد'],
    'political':    ['بيعة', 'خلافة', 'ولاية', 'عزل', 'ملك', 'إمارة', 'تولي'],
    'migration':    ['هجرة', 'هاجر'],
    'construction': ['بناء', 'عمارة', 'تأسيس', 'مسجد'],
    'treaty':       ['صلح', 'عهد', 'معاهدة', 'هدنة'],
    'birth':        ['ولادة', 'مولد', 'ولد'],
    'revelation':   ['نزول', 'وحي', 'آية', 'سورة'],
}
```

**Historical gazetteer**: Use al-Thurayya project (althurayya.github.io) — free, open, ~2K historical Islamic places with coordinates.

### 5.6 Source Registry

```yaml
# sources.yaml
sources:
  - corpus: OpenITI
    repo: 0325AH
    glob: "data/*Tabari*Tarikh*-ara1.mARkdown"
    parser: openiti_markdown
  - corpus: OpenITI
    repo: 0325AH
    glob: "data/*IbnKathir*Bidaya*-ara1.mARkdown"
    parser: openiti_markdown
  - corpus: Shamela
    format: html
    parser: shamela_html
```

### 5.7 Ingestion CLI

```bash
python -m pipeline.ingest                          # all sources
python -m pipeline.ingest --source "0310Tabari..." # one source
python -m pipeline.ingest --source "..." --force   # re-ingest
python -m pipeline.remove --source "..."           # remove source + events
python -m pipeline.status                          # progress report
```

### 5.8 Pipeline Properties

- **Idempotent**: re-run replaces events (DELETE + INSERT per source).
- **Source-scoped**: add/remove sources independently.
- **Resumable**: tracks completed texts + stages. Skips done work.
- **Parallelizable**: Stages 1–2 CPU-bound. Stage 3 rate-limited.
- **Incrementally improvable**: rules-only → +NLP → +LLM. Each stage adds quality.

---

## 6. Project Structure

```
tarikh/
├── api/
│   ├── main.py                 # FastAPI app, lifespan, CORS
│   ├── db.py                   # asyncpg pool, query helpers
│   ├── models.py               # Pydantic models
│   ├── routes/
│   │   ├── events.py
│   │   ├── stats.py
│   │   ├── sources.py
│   │   └── people.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── pipeline/
│   ├── __main__.py             # CLI (ingest/remove/status)
│   ├── registry.py             # reads sources.yaml
│   ├── parsers/
│   │   ├── base.py             # parser ABC
│   │   ├── openiti.py          # mARkdown parser
│   │   └── shamela.py          # future
│   ├── extractors/
│   │   ├── rules.py            # date, type keywords
│   │   ├── nlp.py              # CAMeL NER, argos-translate
│   │   └── llm.py              # Gemini free tier caller
│   ├── gazetteer.py            # al-Thurayya place lookup
│   ├── seeder.py               # → PostgreSQL
│   ├── normalize.py            # type mapping, dedup
│   └── sources.yaml
│
├── db/
│   ├── schema.sql
│   └── migrations/
│
├── web/
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   ├── src/
│   │   ├── main.ts             # Lenis, GSAP, router init
│   │   ├── router.ts           # Barba.js transitions
│   │   ├── api.ts              # fetch + cursor pagination
│   │   ├── pages/
│   │   │   ├── home.ts
│   │   │   ├── timeline.ts
│   │   │   ├── map.ts
│   │   │   ├── event.ts
│   │   │   └── source.ts
│   │   ├── components/
│   │   │   ├── Globe.ts
│   │   │   ├── Timeline.ts
│   │   │   ├── EventCard.ts
│   │   │   ├── Filters.ts
│   │   │   ├── Cursor.ts
│   │   │   └── Skeleton.ts
│   │   ├── styles/
│   │   │   ├── global.css
│   │   │   ├── typography.css
│   │   │   └── animations.css
│   │   └── utils/
│   │       ├── dates.ts
│   │       └── animate.ts
│   └── public/
│       └── fonts/
│
├── design/
│   └── tokens.json
│
├── render.yaml
├── .github/workflows/deploy.yml
└── CLAUDE.md
```

---

## 7. Deployment

### 7.1 Services

| Service  | Platform           | Plan       | Cost   |
|----------|--------------------|------------|--------|
| API      | Render Web Service | Free       | $0     |
| Frontend | Cloudflare Pages   | Free       | $0     |
| Database | Neon PostgreSQL    | Free       | $0     |
| **MVP**  |                    |            | **$0** |

### 7.2 Scale-Up Path

| Trigger                  | Action              | Cost    |
|--------------------------|----------------------|---------|
| Cold starts unacceptable | Render Starter       | +$7/mo  |
| DB > 512MB (~500K events) | Neon Launch          | +$19/mo |
| Custom domain            | Domain registration  | ~$12/yr |
| **Fully scaled**         |                      | **$27/mo** |

### 7.3 render.yaml

```yaml
services:
  - type: web
    name: tarikh-api
    runtime: python
    plan: free
    buildCommand: pip install -r api/requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
    healthCheckPath: /api/v1/stats
    autoDeploy: true
```

Frontend: Cloudflare Pages, connect GitHub, build `cd web && npm ci && npm run build`, output `web/dist`.

### 7.4 CI/CD

```yaml
# .github/workflows/deploy.yml
# push to main:
#   1. Lint + type-check (api + web)
#   2. Build web → Cloudflare Pages
#   3. API auto-deploys via Render
# manual trigger:
#   4. Pipeline ingestion (new sources)
```

---

## 8. Cost Summary

### Running Costs

| Phase      | Events  | DB        | API         | Frontend         | Monthly |
|------------|---------|-----------|-------------|------------------|---------|
| MVP        | <500K   | Neon free | Render free | Cloudflare Pages | $0      |
| Growth     | 500K–2M | Neon $19  | Render $7   | Cloudflare Pages | $26     |
| Full scale | 2M–5M   | Neon $69  | Render $7   | Cloudflare Pages | $76     |

### Ingestion Cost

$0. Hybrid pipeline: rules + NLP extract ~70% for free. LLM (Gemini 3.1/2.5 Flash-Lite free tier) handles summaries + importance at $0. Rate-limited to ~2,000 RPD across 2 models. 5M events completes in ~3.3 months.

---

## 9. Design Handoff

**Figma** (free plan).

1. Design system: colors, typography, spacing, components
2. Desktop: Home, Timeline, Map, Event Detail, Source
3. Mobile responsive
4. Animation specs (duration, easing, triggers)
5. Export → `design/tokens.json`
6. Implement

Palette: dark navy (#0A1628), gold (#D4A853), warm white (#F5F0E8), type accent colors.

---

## 10. Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DB | PostgreSQL + JSONB (Neon) | Document flexibility via JSONB; relational indexes on query columns; pg_trgm Arabic search free; schema evolves without migrations |
| Not pure NoSQL | — | MongoDB Atlas Search is paid; DynamoDB needs GSI design; both cost more at 5M rows |
| Pagination | Cursor-based | O(1) at any depth vs O(n) offset at 5M rows |
| Timeline rendering | Canvas | DOM can't handle 10K+ elements |
| Map clustering | Client-side supercluster | Avoids per-viewport API calls |
| Frontend | Vanilla TS + Vite | No framework runtime; GSAP + Barba handle transitions |
| API | FastAPI | Async, auto docs, Pydantic, smallest footprint |
| Ingestion | 4-stage hybrid | 70% free rules/NLP, 30% free-tier LLM. $0 total |
| LLM | Gemini Flash-Lite free tier | $0 unlimited tokens, rate-limited. Time not a constraint |
| Search | pg_trgm + tsvector | Zero infra; Arabic via 'simple' tokenizer |
| Source management | Source-scoped | Add/remove = DELETE + INSERT. Idempotent |
