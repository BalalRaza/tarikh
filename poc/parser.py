#!/usr/bin/env python3
"""Stage 2: Parse mARkdown → sections.json

OpenITI mARkdown format used by this text:
  ### |   = chapter header (level 1)
  ### ||  = subsection header (level 2) — used as extraction unit
  ### ||| = sub-subsection (included as content)
  # text  = paragraph
  ~~text  = paragraph continuation
  PageV01P001 = page marker (strip)
  ms0001  = manuscript marker (strip)
"""

import json
import argparse
import glob
import re

SOURCE_META = {
    "corpus": "OpenITI",
    "repo": "0325AH",
    "uri": "0310Tabari.Tarikh.Shamela0009783BK1-ara1",
    "author": "al-Tabari",
    "author_death_ah": 310,
    "book": "Tarikh al-Rusul wa'l-Muluk",
}

_PAGE = re.compile(r'PageV\d+P\d+')
_MS   = re.compile(r'\bms\d+\b')


def find_tabari_file():
    matches = glob.glob("0325AH/data/**/*Tabari*Tarikh*.mARkdown", recursive=True)
    if not matches:
        raise FileNotFoundError("Tabari Tarikh file not found. Run fetch_corpus.sh first.")
    return sorted(matches)[0]


def clean(raw):
    s = raw.strip()
    if s.startswith("~~"):
        s = s[2:]
    elif s.startswith("# "):
        s = s[2:]
    elif s.startswith("#"):
        s = s[1:]
    s = _PAGE.sub("", s)
    s = _MS.sub("", s)
    return s.strip()


def _save(sections, lines, h1, h2, offset):
    parts = [clean(l) for l in lines]
    text = " ".join(p for p in parts if p)
    if len(text) > 80 and h1 and "PARATEXT" not in h1:
        sections.append({
            "section_id": f"tabari-tarikh-ev-{len(sections):04d}",
            "section_type": "section",
            "parent_headers": [h for h in [h1, h2] if h],
            "arabic_text": text,
            "char_count": len(text),
            "source": {**SOURCE_META, "section_offset": offset},
        })


def parse(filepath, max_sections, from_hijra=False):
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    body = raw.split("#META#Header#End#", 1)[-1] if "#META#Header#End#" in raw else raw
    lines = body.splitlines()

    # Jump to first year-based (Hijra) chapter if requested
    start_i = 0
    if from_hijra:
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("### |") and not s.startswith("### ||") and "سنة" in s:
                start_i = i
                break
        print(f"Starting from Hijra period (line {start_i})")

    sections = []
    h1 = h2 = ""
    cur_lines = []
    cur_offset = 0

    for i, line in enumerate(lines[start_i:], start=start_i):
        s = line.strip()

        if s.startswith("### |") and not s.startswith("### ||"):
            # Level-1 chapter header
            _save(sections, cur_lines, h1, h2, cur_offset)
            cur_lines = []
            h1 = s[5:].strip()
            h2 = ""
            cur_offset = i

        elif s.startswith("### ||") and not s.startswith("### |||"):
            # Level-2 subsection header — primary extraction boundary
            _save(sections, cur_lines, h1, h2, cur_offset)
            cur_lines = []
            h2 = s[6:].strip()
            cur_offset = i

        elif s.startswith("### |||"):
            # Level-3+ headers folded into text
            txt = s.lstrip("#| ").strip()
            if txt:
                cur_lines.append(f"# {txt}")

        elif s.startswith("# ") or s.startswith("~~") or (s.startswith("#") and not s.startswith("##")):
            cur_lines.append(line)

        if max_sections and len(sections) >= max_sections:
            break

    if cur_lines and (max_sections is None or len(sections) < max_sections):
        _save(sections, cur_lines, h1, h2, cur_offset)

    return sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sections", type=int, default=None)
    ap.add_argument("--from-hijra", action="store_true",
                    help="Start from the first Hijri year section (skip pre-Islamic cosmology)")
    ap.add_argument("--input", default=None, help="Override mARkdown file path")
    args = ap.parse_args()

    filepath = args.input or find_tabari_file()
    print(f"Parsing: {filepath}")
    sections = parse(filepath, args.max_sections, from_hijra=args.from_hijra)
    print(f"Extracted {len(sections)} sections")

    with open("sections.json", "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    print("Saved sections.json")


if __name__ == "__main__":
    main()
