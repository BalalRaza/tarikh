"""Type normalization and event ID generation."""

import re

TYPE_MAP = {
    "battle": "battle",
    "military": "battle",
    "military_mobilization": "battle",
    "political": "political",
    "diplomatic": "political",
    "death": "death",
    "birth": "birth",
    "migration": "migration",
    "revelation": "revelation",
    "miraculous": "revelation",
    "religious": "revelation",
    "treaty": "treaty",
    "social": "social",
    "conversion": "social",
    "construction": "construction",
}


def normalize_type(raw: str) -> str:
    return TYPE_MAP.get(raw.lower().strip(), "other")


def generate_event_id(source_uri: str, date_ce: int | None, title_en: str) -> str:
    """Deterministic event ID: {source_slug}-{date_ce}-{title_slug}"""
    source_slug = source_uri.split(".")[0] if source_uri else "unknown"
    date_part = str(date_ce) if date_ce is not None else "nodate"
    title_slug = title_en.lower().replace(" ", "-")
    title_slug = re.sub(r"[^a-z0-9-]", "", title_slug)[:40]
    return f"{source_slug}-{date_part}-{title_slug}"
