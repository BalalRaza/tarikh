"""Source registry — reads sources.yaml."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

SOURCES_FILE = Path(__file__).parent / "sources.yaml"


@dataclass
class SourceConfig:
    corpus: str
    repo: str
    glob: str
    parser: str
    uri: str
    from_hijra: bool = False
    meta: dict = field(default_factory=dict)


def load_sources(path: Path | None = None) -> list[SourceConfig]:
    """Load source configs from YAML."""
    p = path or SOURCES_FILE
    with open(p) as f:
        data = yaml.safe_load(f)
    return [SourceConfig(**s) for s in data["sources"]]
