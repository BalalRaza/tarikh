# Tarikh — Next Steps

## Status

| Component | Status |
|-----------|--------|
| Neon DB + schema | ✅ Done |
| Pipeline: Stage 1 (rules) | ✅ Done — 10 events seeded |
| Pipeline: Stage 2 (NLP) | ❌ Not built |
| Pipeline: Stage 3 (LLM) | ⚠️ Built, not tested end-to-end |
| API (FastAPI) | ✅ Built — not run against live DB yet |
| Frontend | ✅ Built — Timeline page, builds clean |

---

## Step 1 — Run full pipeline (LLM stage) — ❌ NOT DONE (needs your Mac)

Must run on your machine — sandbox has no network to Neon/Vertex.

Test the LLM stage end-to-end before scaling.

```bash
cd tarikh
python -m pipeline ingest --max-sections 10 --base-dir poc
```

This calls Gemini (via Vertex AI). Verify events in DB have `title_en`, `summary_en`, `importance` populated.

Check:
```bash
python -m pipeline status
```

If LLM stage errors, fix `pipeline/extractors/llm.py` (model names, auth).

---

## Step 2 — Ingest more sections — ❌ NOT DONE (needs your Mac)

Once Stage 3 is verified, ingest the full PoC range:

```bash
python -m pipeline ingest --base-dir poc
```

Target: ~100–300 events. Use `pipeline status` to check counts.

---

## Step 3 — Build the FastAPI backend (`api/`) — ✅ DONE

Built: main.py, db.py, models.py, routes/events.py, routes/stats.py, requirements.txt.
Endpoints: events (filters + cursor + search), events/:id, events/map, stats.
Imports clean. Not yet run against live DB (do on your Mac).

Create `api/` per the LLD. Minimum endpoints to unblock frontend:

```
GET /api/v1/events       — list with filters + cursor pagination
GET /api/v1/events/:id   — full event detail
GET /api/v1/stats        — counts by type/importance
```

Stack: FastAPI + asyncpg + Pydantic v2 + orjson.

See LLD.md §3 for full endpoint spec and query patterns.

Files to create:
```
api/
├── main.py       # FastAPI app, CORS, lifespan
├── db.py         # asyncpg pool
├── models.py     # Pydantic response models
├── routes/
│   ├── events.py
│   └── stats.py
└── requirements.txt
```

---

## Step 4 — Build the frontend (`web/`) — ✅ DONE

Built: Vite + TS scaffold, Timeline page (Canvas pan/zoom/LOD), Lenis smooth scroll.
api.ts typed wrapper with cursor pagination. `npm run build` passes (8 kB gzip).
Next: wire to live API, add map/detail pages later.

Scaffold with Vite + TypeScript. Start with the Timeline page only.

Stack: Vite, TypeScript, GSAP, Canvas timeline renderer, Lenis.

See LLD.md §4 for full component/page breakdown.

Files to create:
```
web/
├── index.html
├── vite.config.ts
├── package.json
└── src/
    ├── main.ts
    ├── api.ts          # fetch wrapper + cursor pagination
    ├── pages/
    │   └── timeline.ts
    └── components/
        └── Timeline.ts # Canvas renderer
```

---

## Step 5 — Stage 2 NLP (optional, add later)

Add `pipeline/extractors/nlp.py` using CAMeL Tools for Arabic NER.

- Extracts: person names, location names
- Gazetteer lookup (`pipeline/gazetteer.py`) → lat/lng from al-Thurayya

Skip for now — Stage 1 (rules) + Stage 3 (LLM) are sufficient for PoC.

---

## Step 6 — Deploy

1. **API** → Render Web Service (free). Wire `DATABASE_URL` env var.
2. **Frontend** → Cloudflare Pages (free). Build: `cd web && npm ci && npm run build`, output `web/dist`.

See LLD.md §7 for `render.yaml` and CI/CD config.

---

## Next source texts (after PoC)

| Priority | Text | Repo |
|----------|------|------|
| 1 | Ibn Hisham's Sira | `0225AH` |
| 2 | Ibn Sa'd's Tabaqat | `0230AH` |
| 3 | Ibn Kathir's al-Bidaya | `0775AH` |

Add each to `pipeline/sources.yaml` — pipeline handles the rest.
