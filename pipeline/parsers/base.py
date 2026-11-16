"""Base parser ABC."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Section:
    """One extraction unit from a source text."""

    section_id: str
    arabic_text: str
    parent_headers: list[str] = field(default_factory=list)
    char_count: int = 0
    source_uri: str = ""
    source_offset: int = 0

    def __post_init__(self):
        if not self.char_count:
            self.char_count = len(self.arabic_text)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, filepath: str, *, max_sections: int | None = None) -> list[Section]:
        """Parse a source file into sections."""
        ...
