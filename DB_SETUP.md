# Neon PostgreSQL Setup

## 1. Create Neon Account & Project

1. Go to [neon.tech](https://neon.tech) → Sign up (GitHub/Google)
2. Create project: name it `tarikh`, region `us-east-1` (closest to Render free tier)
3. Default branch `main` is fine

## 2. Get Connection String

After project creation, Neon shows the connection string. Copy it.

Format: `postgresql://user:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require`

## 3. Create `.env`

In project root (`tarikh/`):

```
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=google_app_credentials.json
```

Place your `google_app_credentials.json` service account file in the project root.

## 4. Create Virtual Environment

```bash
cd tarikh
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 5. Run Schema

Option A — Neon SQL Editor (web UI):
1. Go to Neon dashboard → SQL Editor
2. Paste contents of `db/schema.sql`
3. Run

Option B — psql CLI:
```bash
psql "$DATABASE_URL" -f db/schema.sql
```

## 6. Verify

```bash
psql "$DATABASE_URL" -c "\dt"
```

Should show `sources` and `events` tables.

## Notes

- Free tier: 512MB storage, 100 compute-hours/mo, auto-suspend after 5min idle
- Connection pooler enabled by default. Use the pooled connection string for the API server (swap `-pooler` into the hostname)
- For the ingestion pipeline, use the direct (non-pooled) connection string
