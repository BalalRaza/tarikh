# Tarikh — handoff (2026-11-17)

Context from a planning and design conversation. Read this before working.

## Product

- Mobile-first visual timeline of the Seerah. For kids (5+) and adults: exploration and quick checks.
- English primary, Arabic secondary. Sunni mainstream sources only.
- First release: Seerah only (birth to the Farewell Pilgrimage).

## Decisions

**Depiction**
- The Prophet ﷺ: only a shapeless glowing dot, whitish-yellow, fully blurred. Draw it in code, never with an image model.
- Other prophets, angels, companions: no figures. Silhouettes only.

**Sources**
- Tier 1: Quran (quran.com), graded hadith (sunnah.com; always read the grade).
- Tier 2: Ibn Kathir, al-Bidaya wa'l-Nihaya; Ibn Hisham, Sira.
- No tier 3. al-Tabari stays in the database as archive only: never queued, never public.
- A scholar or teacher will approve the whitelist. Not done yet.

**Grade per event**
- A: Quran or sahih hadith supports it.
- B: two classical sources agree.
- C: one source only.
- D: sources conflict; show both.

**Design (approved)**
- Timeline is the app. Angled line from bottom-left to top-right. Drag along it; tap a point to focus; tap the bottom card to open the event.
- Major events: large yellow points. Minor: small teal points. Evenly spaced, not to scale.
- Full-page map behind the line, monotone and dimmed. It pans so the focused event's place sits under the focus point, where a glow rests.
- Auto-zoom: when neighbouring events are close together, zoom in and reveal local places (Kaaba, Hira, Arafat, Hudaybiyyah; Prophet's Mosque, Uhud, the Trench, Quba).
- Event page: scene on top, small circular map top right showing only the place, when/where, short plain text, fuller text, source grade with references.
- Palette: ink #0E2233 / #16324A, sun yellow #F7C948, teal #7FD3DE / #0F6E7C, light ground #F2F7FB.
- Type: Baloo 2 (headings), Nunito (body), Baloo Bhaijaan 2 (Arabic).
- Rejected: chapter/story-list layout; "road ahead" perspective timeline; small corner map on the timeline.

Prototype source is in `design/prototype/` (three `.dc.html` files from the Design canvas; the logic is in the script block at the bottom of each). Canvas: https://claude.ai/artifact/QUfDig4XZWQu3nCgV3Ruh7

## Next build: static demo

- Static site, no database or API. 13 events hardcoded in one JSON file.
- Each event: date (CE and AH), place with real coordinates, short text, fuller text, Ibn Kathir reference (volume and chapter heading, plus Arabic passage), hadith references with sunnah.com links, grade.
- Every sunnah.com link must be opened and checked against the claim.
- Scenes: one per event, designed on the Design canvas and exported as images (vector compositions, not painted art).
- Target URL: braza.in/tarikh. Build with base path `/tarikh/`. Routing depends on where the `website` repo is hosted: still unknown.
- Purpose: show a friend for feedback.

The 13 sample events (dates are from general knowledge, NOT yet verified against the sources):
birth (c. 570), marriage to Khadijah (c. 595), first revelation (610), migration to Abyssinia (c. 615), Year of Sorrow (c. 619), Night Journey (c. 621), Hijra (622 / 1 AH), Badr (624 / 2 AH), Uhud (625 / 3 AH), the Trench (627 / 5 AH), Hudaybiyyah (628 / 6 AH), Conquest of Makkah (630 / 8 AH), Farewell Pilgrimage (632 / 10 AH).

## Later: intake and review system

- Staged intake with a cap (about 20 candidates a day), each stored with its Arabic passage, landing as `pending`.
- Review in a CMS (suggested: Directus run locally on the same Postgres) plus a preview route.
- Verifier agent: checks each candidate against the whitelist, stores grade and citations.
- Image generator agent with a fixed style block and reference images, plus a checker agent for the depiction rules.
- `db/migrations/001_staging.sql` is written but NOT run: adds status, locked, passage_ar, grade, citations, and an `intakes` table; marks al-Tabari events as archive.
- Pipeline code changes still to do: seeder skips locked rows; `--force` spares approved and locked; intake command with cap; API returns only approved; per-source start and end range (Ibn Kathir covers far more than the Seerah).

## Known issues

- `pipeline/extractors/llm.py` calls `gemini-2.5-flash-lite` and `gemini-2.5-flash` on Vertex AI. Reports say both were retired there on 2026-10-20. Confirm the replacement IDs your project can call, test on 10 PoC sections, then change `MODELS`.
- Ibn Kathir and Ibn Hisham texts are not on disk. Only OpenITI `0325AH` is cloned.
- `plan-my-trip-…json` in the project root looks like a cloud service-account key. Keep it out of git.
- The existing `web/` (dark canvas timeline) and `LLD.md` describe the old direction: an Arabic-primary research tool for millions of events. The data layer carries over; the front end does not.

## Open questions

1. Where is the `website` repo hosted (decides how `/tarikh` is routed)?
2. Does the glow on the map only ever mean the Prophet ﷺ, or may it mark an event's place (e.g. Abyssinia, where he was not present)?
3. Zoom rule: keep "neighbours are close", or switch to "place is inside a city"? Add zoom-out, travel, zoom-in for long jumps between two zoomed places?
