"""OpenITI mARkdown parser."""

import re

from .base import BaseParser, Section

_PAGE = re.compile(r"PageV\d+P\d+")
_MS = re.compile(r"\bms\d+\b")


def _clean(raw: str) -> str:
    s = raw.strip()
    if s.startswith("~~") or s.startswith("# "):
        s = s[2:]
    elif s.startswith("#"):
        s = s[1:]
    s = _PAGE.sub("", s)
    s = _MS.sub("", s)
    return s.strip()


def _save(
    sections: list[Section], lines: list[str], h1: str | None, h2: str | None, offset: int, source_uri: str, slug: str
) -> None:
    parts = [_clean(line) for line in lines]
    text = " ".join(p for p in parts if p)
    if len(text) > 80 and h1 and "PARATEXT" not in h1:
        sections.append(
            Section(
                section_id=f"{slug}-{len(sections):04d}",
                arabic_text=text,
                parent_headers=[h for h in [h1, h2] if h],
                source_uri=source_uri,
                source_offset=offset,
            )
        )


class OpenITIParser(BaseParser):
    def __init__(self, source_uri: str, from_hijra: bool = False):
        self.source_uri = source_uri
        self.from_hijra = from_hijra
        # uri_slug: last part of source_uri before "-ara"
        base = source_uri.split("/")[-1]
        self.slug = base.split("-ara")[0] if "-ara" in base else base

    def parse(self, filepath: str, *, max_sections: int | None = None) -> list[Section]:
        sections: list[Section] = []
        h1: str | None = None
        h2: str | None = None
        buf: list[str] = []
        buf_offset: int = 0
        started = not self.from_hijra

        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        # Skip metadata header
        if "#META#Header#End#" in raw:
            raw = raw.split("#META#Header#End#", 1)[1]

        all_lines = raw.splitlines(keepends=True)
        offset = 0
        for line in all_lines:
            stripped = line.rstrip("\n")

            if stripped.startswith("### |||"):
                # sub-subsection: fold into body
                if started:
                    buf.append(stripped[7:].strip())

            elif stripped.startswith("### ||"):
                # level-2 boundary: save current buffer, start new section
                _save(sections, buf, h1, h2, buf_offset, self.source_uri, self.slug)
                if max_sections and len(sections) >= max_sections:
                    return sections
                h2 = stripped[6:].strip()
                buf = []
                buf_offset = offset

                if not started and "سنة" in h2:
                    started = True

            elif stripped.startswith("### |"):
                # level-1 chapter header
                _save(sections, buf, h1, h2, buf_offset, self.source_uri, self.slug)
                if max_sections and len(sections) >= max_sections:
                    return sections
                new_h1 = stripped[5:].strip()
                h2 = None
                buf = []
                buf_offset = offset

                if not started and "سنة" in new_h1:
                    started = True

                h1 = new_h1

            elif started and (
                stripped.startswith("# ")
                or stripped.startswith("~~")
                or (stripped.startswith("#") and not stripped.startswith("##"))
            ):
                buf.append(stripped)

            offset += len(line)

        _save(sections, buf, h1, h2, buf_offset, self.source_uri, self.slug)
        return sections
