#!/usr/bin/env python3
"""Stage 4: Deduplicate raw_events.json → events.json"""

import json
import re


def tokenize(text):
    if not text:
        return set()
    return set(re.findall(r"\w+", text.lower()))


def token_overlap(a, b):
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_duplicate(a, b, year_window=2):
    # Must be within year_window years
    ka, kb = a.get("sort_key"), b.get("sort_key")
    if ka is None or kb is None:
        return False
    if abs(ka - kb) > year_window:
        return False
    # Title overlap > 0.7
    return token_overlap(a.get("title_en", ""), b.get("title_en", "")) > 0.7


def merge(a, b):
    """Keep richest fields, merge people arrays."""
    # Pick longer summaries
    for field in ("summary_en", "summary_ar"):
        if len(b.get(field) or "") > len(a.get(field) or ""):
            a[field] = b[field]
    # Merge people by name_en dedup
    existing_names = {p.get("name_en") for p in a.get("people", [])}
    for p in b.get("people", []):
        if p.get("name_en") not in existing_names:
            a.setdefault("people", []).append(p)
            existing_names.add(p.get("name_en"))
    # Keep higher confidence
    if b.get("confidence", 0) > a.get("confidence", 0):
        a["confidence"] = b["confidence"]
    return a


def dedup(events):
    merged = []
    used = set()
    for i, ev in enumerate(events):
        if i in used:
            continue
        canonical = dict(ev)
        for j in range(i + 1, len(events)):
            if j in used:
                continue
            if is_duplicate(canonical, events[j]):
                canonical = merge(canonical, events[j])
                used.add(j)
                print(f"  Merged: '{events[j].get('title_en')}' → '{canonical.get('title_en')}'")
        merged.append(canonical)
    return merged


def assign_ids(events):
    seen = {}
    for ev in events:
        slug = re.sub(r"\W+", "-", (ev.get("title_en") or "").lower()).strip("-")[:40]
        sk = ev.get("sort_key") or "unknown"
        base = f"tabari-{sk}-{slug}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        ev["event_id"] = base if n == 0 else f"{base}-{n}"
    return events


def main():
    with open("raw_events.json", encoding="utf-8") as f:
        events = json.load(f)
    print(f"Loaded {len(events)} raw events")

    # Sort by sort_key first for deterministic grouping
    events.sort(key=lambda e: (e.get("sort_key") is None, e.get("sort_key") or 0))

    deduped = dedup(events)
    deduped = assign_ids(deduped)

    print(f"After dedup: {len(deduped)} unique events ({len(events) - len(deduped)} merged)")

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print("Saved events.json")


if __name__ == "__main__":
    main()
