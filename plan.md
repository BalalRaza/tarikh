# PoC LLD — Islamic History Timeline

## Scope

Extract historical events from the OpenITI corpus (machine-readable Arabic primary sources on GitHub), process through Gemini for structured event extraction, store as JSON, render as a zoomable HTML timeline.

---

## Why OpenITI

OpenITI gives us the **actual primary sources** — al-Tabari's chronicle, Ibn Hisham's Sira, biographical dictionaries — already in a machine-readable format with structural annotations.

Key advantages:
- **Primary sources**, not derived data
- **Already machine-readable** (mARkdown format, not HTML scraping)
- **Pre-tagged structure**: `### @` = event sections, `### $` = biography sections
- **Full provenance**: author, book, edition, version all encoded in the URI
- **Scholarly metadata**: YAML files per text with dates, attributions, tags
- **Open license**: free for academic/research use
- **Massive scale**: 25,000+ texts, but we pick exactly what we need

---

## OpenITI corpus structure (what we're working with)

```
GitHub org: github.com/OpenITI
├── 0025AH/          # Authors who died 1–25 AH
│   └── data/
│       └── {AuthorURI}/
│           └── {BookURI}/
│               ├── {VersionURI}.mARkdown   # The text
│               ├── {VersionURI}.yml         # Version metadata
│               ├── {BookURI}.yml            # Book metadata
│               └── {AuthorURI}.yml          # Author metadata
├── 0050AH/          # Authors who died 26–50 AH
├── 0075AH/          # Authors who died 51–75 AH
│   ...
└── 1450AH/          # Most recent period
```

**URI format example:**
`0310Tabari.Tarikh.Shamela0009783-ara1.mARkdown`
- `0310` = author death year (310 AH)
- `Tabari` = author name
- `Tarikh` = book title
- `Shamela0009783` = source/edition
- `ara1` = Arabic, version 1

**mARkdown tags we care about:**
- `### @` — event description (historical chronicles use these)
- `### $` — biography entry (biographical dictionaries use these)
- `### |` / `### ||` / `### |||` — chapter/section/subsection headers
- `#META#Header#End#` — separates metadata header from body

---

## Target texts for PoC

For pre-Islamic + early Islamic events, we need two types of source texts:

| Text | Author | Died | Repo | Why |
|------|--------|------|------|-----|
| Tarikh al-Rusul wa'l-Muluk | al-Tabari | 310 AH | `0325AH` | **The** universal history. Covers creation → 915 CE. Chronological/annalistic format — events organized by year. Ideal for timeline extraction. |
| al-Sira al-Nabawiyya | Ibn Hisham | 218 AH | `0225AH` | Biography of the Prophet ﷺ. Covers pre-Islamic context + Seerah. |

**PoC scope:** Extract events from ONE text (al-Tabari's Tarikh, pre-Islamic + early Islamic sections only). This alone should yield 50–200 events.

---

## Architecture (4 stages)

```
[OpenITI repo clone] → raw mARkdown → [Parser] → sections → [Gemini] → structured events → [Store] → events.json → [Timeline UI]
```

---

## Stage 1: Corpus access

**Method:** Shallow clone the specific repo from GitHub.

```bash
git clone --depth 1 https://github.com/OpenITI/0325AH.git
```

**Then locate al-Tabari's Tarikh:**
```bash
find 0325AH/data -name "*Tabari*Tarikh*" -type f
```

The text will be a large file (Tarikh is ~1.6 million words). We don't process the whole thing — we target specific sections.

**Alternative:** Download just the file via GitHub raw URL if the repo is too large.

**Output:** Raw `.mARkdown` file on disk.

---

## Stage 2: mARkdown parser (Python, no LLM)

This is the cheap, deterministic step. Parse the mARkdown structure to extract discrete sections.

**What the parser does:**
1. Skip everything before `#META#Header#End#`
2. Split text on `### @` (event) and `### $` (biography) markers
3. For each section, also capture its parent chapter headers (`### |`, `### ||`) for context
4. Extract any embedded date references (Hijri years often appear as numbers in the text)

**Key detail:** al-Tabari's Tarikh is organized annalistically — chapter headers often contain the year:
```
### | ذكر الخبر عن أمر النبي ﷺ في سنة ثمان من الهجرة
```
(Mention of events in year 8 of the Hijra)

The parser extracts these header-embedded dates when possible.

**Output per section:**
```json
{
  "section_id": "tabari-tarikh-ev-0042",
  "section_type": "event",          // "event" or "biography"
  "parent_headers": [
    "ذكر ما كان من أمر رسول الله في السنة الثانية من الهجرة",
    "ذكر غزوة بدر الكبرى"
  ],
  "arabic_text": "...(raw Arabic text of the section)...",
  "char_count": 2340,
  "source": {
    "corpus": "OpenITI",
    "repo": "0325AH",
    "uri": "0310Tabari.Tarikh.Shamela0009783-ara1",
    "author": "al-Tabari",
    "author_death_ah": 310,
    "book": "Tarikh al-Rusul wa'l-Muluk",
    "section_offset": 145023
  }
}
```

**Scope filtering:** For the PoC, we only process sections from the beginning of the text up to ~the first 50 AH (covering pre-Islamic + Seerah + early Rashidun). This keeps the Gemini API cost manageable.

**Output:** `sections.json` — array of parsed sections.

---

## Stage 3: Gemini extraction

**Input:** One parsed section at a time.

**System prompt (draft):**

```
You are extracting structured timeline events from classical Arabic
historical texts for an Islamic history timeline project.

The source text is from al-Tabari's Tarikh al-Rusul wa'l-Muluk,
a 10th-century CE annalistic chronicle. The text is in Arabic.

Given a section of the chronicle with its parent chapter headers,
extract ALL discrete historical events mentioned.

For each event, output:
- title_ar: Arabic title (short, 5-10 words)
- title_en: English title
- event_type: battle | treaty | birth | death | migration | revelation |
              political | construction | social | other
- date_ah: Hijri year (integer). null if not determinable.
- date_ce: Gregorian year (integer, negative for BCE). null if unknown.
- date_precision: day | month | year | decade | approximate
- location: { name_ar, name_en, lat, lng } — lat/lng only if confident
- summary_ar: 1-2 sentence Arabic summary from the source text
- summary_en: 1-2 sentence English summary
- people: Array of { name_ar, name_en, role }
- importance: 1 (era-defining) | 2 (significant) | 3 (minor detail)
- confidence: 0.0–0.95
- confidence_reasoning: Why this score

RULES:
- The Arabic text IS the primary source. Extract what it says.
- Translate names and terms accurately.
- Do NOT add information not present in the source text.
- If the section's parent headers contain a date, use it.
- If a date is mentioned only as relative ("in that year"), resolve
  it from the chapter header context provided.
- Multiple events may exist in one section. Extract all of them.

Respond with ONLY a JSON array. No markdown, no preamble.
```

**Batching:** Group small sections (< 500 chars) into batches of 3–5 per API call to reduce call count.

**Post-processing (Python):**
1. Validate JSON response
2. Compute `sort_key` from `date_ce` or `date_ah`
3. Convert AH↔CE using `hijri-converter` library (cross-check Gemini's conversion)
4. Attach full provenance from Stage 2's `source` object
5. Generate stable `event_id`: `{source_uri}-{sort_key}-{slug(title_en)}`

**Output:** `raw_events.json`

---

## Stage 4: Deduplication

Same approach as v1, but simpler because we're working from a single source text (al-Tabari). Duplicates arise when:
- The same event is mentioned in both a chapter header and the body
- The same event appears in multiple sections (e.g., referenced across years)

**Merge logic:**
1. Group by `sort_key` proximity (±2 years) + title similarity (token overlap > 0.7)
2. Keep the richest version (longest summary, most people)
3. Merge people arrays
4. Log merges

**Output:** `events.json` — final, deduplicated.

---

## Stage 5: Timeline UI

Same as v1 — single HTML file, vis-timeline, level-of-detail zoom.

One addition for this version:

**Bilingual display:** Each event card shows both Arabic and English titles/summaries. The Arabic text is the primary source; the English is the Gemini translation. This lets reviewers verify accuracy at a glance.

**Source link:** Each event links back to the OpenITI text (GitHub raw URL + character offset), so a reviewer can read the original passage in context.

---

## File structure

```
poc/
├── fetch_corpus.sh       # Stage 1: clone repo, locate text
├── parser.py             # Stage 2: parse mARkdown → sections
├── extractor.py          # Stage 3: call Gemini per section
├── dedup.py              # Stage 4: merge duplicates
├── run_pipeline.py       # Orchestrator
├── sections.json         # Stage 2 output
├── raw_events.json       # Stage 3 output
├── events.json           # Stage 4 output (final)
├── timeline.html         # Stage 5: the UI
└── .env                  # GEMINI_API_KEY=...
```

---

## Pipeline run sequence

```
1. bash fetch_corpus.sh
   → Clones 0325AH repo, locates Tarikh file

2. python run_pipeline.py --parse --max-sections 100
   → Parses mARkdown, extracts first 100 event/bio sections
   → Saves sections.json

3. python run_pipeline.py --extract
   → Sends sections to Gemini, gets structured events
   → Saves raw_events.json

4. python run_pipeline.py --dedup
   → Merges duplicates
   → Saves events.json

5. Open timeline.html in browser
```

---

## Expected output volume

- 1 text (al-Tabari's Tarikh, pre-Islamic + early Islamic sections)
- ~50–100 sections parsed from the target date range
- ~100–300 raw events extracted
- ~60–150 unique events after dedup
- Timeline spanning ~500 BCE – 50 AH (~670 CE)

---

## Cost estimate (Gemini API)

- ~100 sections × ~2000 chars avg = ~200K input chars
- At Gemini's pricing, this is well under $1 for the PoC
- Each section produces ~500 chars output
- Total: negligible cost

---

## What this PoC validates

1. Can we parse OpenITI mARkdown reliably? (Structure, edge cases, header extraction)
2. Does Gemini extract accurate events from classical Arabic text? (Quality, date accuracy, hallucination rate)
3. Does annalistic chapter structure give us dates for free? (Huge advantage of al-Tabari)
4. Is bilingual output (Arabic + English) usable for review?
5. Does provenance chain (OpenITI → section → event) hold up?
6. Does the timeline UI handle the event density?

---

## What this PoC does NOT cover

- Multiple source texts (just al-Tabari for now)
- Cross-source conflict detection (single source)
- Hadith citations (al-Tabari uses isnad chains, but citation linking is future work)
- Human review CMS
- Nightly scheduling
- Authentication / deployment

---

## Future: scaling beyond the PoC

Once validated, the pipeline scales by adding more texts:

| Priority | Text | Events it adds |
|----------|------|---------------|
| 1 | Ibn Hisham's Sira (0225AH) | Detailed Seerah events |
| 2 | Ibn Sa'd's Tabaqat (0230AH) | Companion biographies |
| 3 | Ibn Kathir's al-Bidaya (0775AH) | Cross-reference & fill gaps |
| 4 | al-Dhahabi's Tarikh al-Islam (0750AH) | Comprehensive biographical data |
| 5 | Khalifa b. Khayyat's Tarikh (0240AH) | Earliest surviving chronicle |

Each new text reuses the same pipeline (parse → extract → dedup → merge into events.json). The dedup stage becomes cross-source conflict detection at that point.