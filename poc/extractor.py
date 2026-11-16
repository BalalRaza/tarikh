#!/usr/bin/env python3
"""Stage 3: Call Gemini per section → raw_events.json"""

import json
import os
import re
import time

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(
    vertexai=True,
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)

SYSTEM_PROMPT = """You are extracting structured timeline events from classical Arabic historical texts for an Islamic history timeline project.

The source text is from al-Tabari's Tarikh al-Rusul wa'l-Muluk, a 10th-century CE annalistic chronicle.

Given one or more sections of the chronicle (each with parent chapter headers), extract ALL discrete historical events mentioned.

For each event output:
- title_ar: Arabic title (5-10 words)
- title_en: English title
- event_type: battle | treaty | birth | death | migration | revelation | political | construction | social | other
- date_ah: Hijri year (integer). null if not determinable.
- date_ce: Gregorian year (integer, negative for BCE). null if unknown.
- date_precision: day | month | year | decade | approximate
- location: { name_ar, name_en, lat, lng } — lat/lng only if confident, else null
- summary_ar: 1-2 sentence Arabic summary from source text
- summary_en: 1-2 sentence English summary
- people: array of { name_ar, name_en, role }
- importance: 1 (era-defining) | 2 (significant) | 3 (minor detail)
- confidence: 0.0–0.95
- confidence_reasoning: why this score

RULES:
- The Arabic text IS the primary source. Extract only what it says.
- Do NOT add information not present in the source text.
- If parent headers contain a date, use it.
- Multiple events may exist in one section. Extract all of them.

Respond with ONLY a JSON array. No markdown, no preamble."""


def ah_to_ce(ah):
    """Approximate AH → CE conversion."""
    if ah is None:
        return None
    return round(ah - ah / 33 + 622)


def build_prompt(sections):
    parts = [SYSTEM_PROMPT, ""]
    for i, s in enumerate(sections):
        if len(sections) > 1:
            parts.append(f"--- Section {i + 1} ---")
        if s["parent_headers"]:
            parts.append("Parent headers: " + " > ".join(s["parent_headers"]))
        parts.append("Text:")
        parts.append(s["arabic_text"])
        parts.append("")
    return "\n".join(parts)


def _retry_delay(err):
    """Parse suggested retry delay from 429 error, default 60s."""
    m = re.search(r'retry in (\d+\.?\d*)s', str(err), re.IGNORECASE)
    return float(m.group(1)) + 3 if m else 60.0


def call_gemini(sections, retries=5):
    prompt = build_prompt(sections)
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                delay = _retry_delay(err)
                print(f"\n  Rate limited. Waiting {delay:.0f}s...", flush=True)
                time.sleep(delay)
            else:
                print(f"  Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
    return []


def post_process(events, sections):
    """Add provenance and compute sort_key."""
    source = sections[0]["source"] if sections else {}
    for ev in events:
        # Cross-check / fill AH↔CE
        if ev.get("date_ah") and not ev.get("date_ce"):
            ev["date_ce"] = ah_to_ce(ev["date_ah"])
        # sort_key: prefer CE, fall back to derived from AH
        ev["sort_key"] = ev.get("date_ce") or (ah_to_ce(ev.get("date_ah")) if ev.get("date_ah") else None)
        ev["source"] = source
    return events


def make_batches(sections, small_threshold=500, batch_size=5):
    """Group small sections into batches; large sections go alone."""
    batches = []
    pending = []
    for s in sections:
        if s["char_count"] < small_threshold:
            pending.append(s)
            if len(pending) >= batch_size:
                batches.append(pending)
                pending = []
        else:
            if pending:
                batches.append(pending)
                pending = []
            batches.append([s])
    if pending:
        batches.append(pending)
    return batches


def main():
    with open("sections.json", encoding="utf-8") as f:
        sections = json.load(f)

    print(f"Loaded {len(sections)} sections")
    batches = make_batches(sections)
    print(f"Processing {len(batches)} batches...")

    all_events = []
    for i, batch in enumerate(batches):
        print(f"  Batch {i + 1}/{len(batches)} ({len(batch)} section(s))...", end=" ", flush=True)
        events = call_gemini(batch)
        events = post_process(events, batch)
        all_events.extend(events)
        print(f"→ {len(events)} events")
        time.sleep(5)  # free tier: ~15 RPM = 4s/req minimum

    print(f"Total raw events: {len(all_events)}")
    with open("raw_events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    print("Saved raw_events.json")


if __name__ == "__main__":
    main()
