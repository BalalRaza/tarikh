"""Historical Islamic place gazetteer.

Stub with hardcoded common places from early Islamic history.

TODO: load full al-Thurayya dataset (~2K places) from CSV once available.
      See: https://althurayya.github.io/
"""

from dataclasses import dataclass, field


@dataclass
class Place:
    name_ar: str
    name_en: str
    lat: float
    lng: float
    aliases: list[str] = field(default_factory=list)  # alternate Arabic spellings


PLACES: list[Place] = [
    Place("مكة", "Mecca", 21.4225, 39.8262, ["مكة المكرمة", "بكة"]),
    Place("المدينة", "Medina", 24.4686, 39.6142, ["المدينة المنورة", "يثرب"]),
    Place("دمشق", "Damascus", 33.5138, 36.2765, ["الشام"]),
    Place("بغداد", "Baghdad", 33.3152, 44.3661, ["مدينة السلام"]),
    Place("القدس", "Jerusalem", 31.7683, 35.2137, ["بيت المقدس", "إيلياء", "أورشليم"]),
    Place("الكوفة", "Kufa", 32.0297, 44.4019, ["كوفة"]),
    Place("البصرة", "Basra", 30.5085, 47.7804, ["بصرة"]),
    Place("كربلاء", "Karbala", 32.6160, 44.0242, ["كربلا", "الطف"]),
    Place("القاهرة", "Cairo", 30.0444, 31.2357, ["مصر", "الفسطاط"]),
    Place("الحبشة", "Abyssinia", 9.145, 40.4897, ["إثيوبيا", "أكسوم"]),
    Place("الطائف", "Taif", 21.2703, 40.4158, ["طائف"]),
    Place("بدر", "Badr", 23.7781, 38.7916, []),
    Place("أحد", "Uhud", 24.5024, 39.6115, ["جبل أحد"]),
    Place("خيبر", "Khaybar", 25.6981, 39.2936, []),
    Place("تبوك", "Tabuk", 28.3838, 36.5550, []),
    Place("الحيرة", "Hira", 31.9750, 44.4333, ["حيرة"]),
    Place("صنعاء", "Sanaa", 15.3694, 44.1910, ["صنعا"]),
    Place("الري", "Ray", 35.5897, 51.4328, ["ري", "طهران"]),
    Place("نيسابور", "Nishapur", 36.2130, 58.7960, ["نيشابور"]),
    Place("سمرقند", "Samarkand", 39.6542, 66.9597, ["سمرقنд"]),
    Place("الأندلس", "Al-Andalus", 37.3891, -5.9845, ["أندلس", "إسبانيا"]),
    Place("حران", "Harran", 36.8617, 39.0314, ["هران"]),
    Place("الموصل", "Mosul", 36.3350, 43.1189, ["موصل"]),
    Place("واسط", "Wasit", 32.4833, 45.8167, []),
    Place("مرو", "Merv", 37.6536, 62.1819, ["مرو الشاهجان"]),
    Place("بخارى", "Bukhara", 39.7747, 64.4286, ["بخارا"]),
    Place("الإسكندرية", "Alexandria", 31.2001, 29.9187, ["إسكندرية"]),
    Place("قرطبة", "Cordoba", 37.8882, -4.7794, ["قرطبة"]),
    Place("المدائن", "Ctesiphon", 33.0936, 44.5778, ["طيسفون", "سلوقية"]),
    Place("حمص", "Homs", 34.7324, 36.7137, ["حمص"]),
]


def _normalize(name: str) -> str:
    """Strip ال prefix and strip whitespace."""
    name = name.strip()
    if name.startswith("ال"):
        name = name[2:]
    return name


def lookup(name_ar: str) -> tuple[float, float] | None:
    """Fuzzy match an Arabic place name. Returns (lat, lng) or None."""
    needle = _normalize(name_ar)

    for place in PLACES:
        # Exact match on canonical name or aliases
        candidates = [place.name_ar] + place.aliases
        for candidate in candidates:
            if candidate == name_ar:
                return (place.lat, place.lng)

        # Normalized substring match
        norm_candidates = [_normalize(c) for c in candidates]
        for nc in norm_candidates:
            if needle and (needle in nc or nc in needle):
                return (place.lat, place.lng)

    return None
