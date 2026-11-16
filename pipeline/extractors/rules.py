"""Stage 1: rule-based extractor."""

from dataclasses import dataclass

from pipeline.parsers.base import Section

ARABIC_ONES = {
    "إحدى": 1,
    "اثنتي": 2,
    "اثنتين": 2,
    "اثنين": 2,
    "ثلاث": 3,
    "أربع": 4,
    "خمس": 5,
    "ست": 6,
    "سبع": 7,
    "ثمان": 8,
    "ثماني": 8,
    "تسع": 9,
}
ARABIC_TENS = {
    "عشر": 10,
    "عشرة": 10,
    "عشرين": 20,
    "ثلاثين": 30,
    "أربعين": 40,
    "خمسين": 50,
    "ستين": 60,
    "سبعين": 70,
    "ثمانين": 80,
    "تسعين": 90,
}
ARABIC_HUNDREDS = {
    "مئة": 100,
    "مائة": 100,
    "مائتين": 200,
    "مئتين": 200,
    "ثلاثمائة": 300,
    "ثلاثمئة": 300,
    "أربعمائة": 400,
    "أربعمئة": 400,
    "خمسمائة": 500,
    "خمسمئة": 500,
    "ستمائة": 600,
    "ستمئة": 600,
    "سبعمائة": 700,
    "سبعمئة": 700,
    "ثمانمائة": 800,
    "ثمانمئة": 800,
    "تسعمائة": 900,
    "تسعمئة": 900,
}

TYPE_KEYWORDS = {
    "battle": ["غزوة", "غزو", "وقعة", "معركة", "فتح", "حرب", "سرية", "حصار"],
    "death": ["وفاة", "موت", "مقتل", "قتل", "هلاك", "استشهاد"],
    "political": ["بيعة", "خلافة", "ولاية", "عزل", "ملك", "إمارة", "تولي"],
    "migration": ["هجرة", "هاجر"],
    "construction": ["بناء", "عمارة", "تأسيس", "مسجد"],
    "treaty": ["صلح", "عهد", "معاهدة", "هدنة"],
    "birth": ["ولادة", "مولد", "ولد"],
    "revelation": ["نزول", "وحي", "آية", "سورة"],
    "social": ["إسلام", "تحول", "اعتناق"],
}


def ah_to_ce(ah: int | str | None) -> int | None:
    if ah is None:
        return None
    try:
        ah = int(ah)
    except (TypeError, ValueError):
        return None
    return round(ah - ah / 33 + 622)


def _parse_arabic_year(text: str) -> int | None:
    """Parse an Arabic year number from text following 'سنة'."""
    idx = text.find("سنة")
    if idx == -1:
        return None
    words = text[idx + 3 :].split()
    hundreds = 0
    tens = 0
    ones = 0
    for word in words:
        # Strip leading و (and) — can be separate or prefixed
        if word == "و":
            continue
        w = word[1:] if word.startswith("و") else word
        if w in ARABIC_HUNDREDS:
            hundreds = ARABIC_HUNDREDS[w]
        elif w in ARABIC_TENS:
            tens = ARABIC_TENS[w]
        elif w in ARABIC_ONES:
            ones = ARABIC_ONES[w]
        else:
            break
    total = hundreds + tens + ones
    return total if total else None


def _extract_date_ah(section: Section) -> int | None:
    for header in section.parent_headers:
        result = _parse_arabic_year(header)
        if result is not None:
            return result
    return None


def _extract_event_type(section: Section) -> str:
    for text in [*section.parent_headers, section.arabic_text]:
        for event_type, keywords in TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return event_type
    return "other"


@dataclass
class RuleResult:
    date_ah: int | None = None
    date_ce: int | None = None
    sort_key: int | None = None
    event_type: str = "other"


def extract_rules(section: Section) -> RuleResult:
    """Run all rule-based extractors on a section."""
    date_ah = _extract_date_ah(section)
    date_ce = ah_to_ce(date_ah)
    return RuleResult(
        date_ah=date_ah,
        date_ce=date_ce,
        sort_key=date_ce,
        event_type=_extract_event_type(section),
    )
