"""
Event classifier: returns (category, confidence) and (side, side_confidence).

Side classification (Middle East OSINT context):
  red     — hostile / adversary operations (Hamas, Hezbollah, PIJ, Iran-backed)
  blue    — Israeli / IDF operations and statements
  neutral — civilian, humanitarian, political, international community, unknown
"""

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "military": [
        "attack", "strike", "missile", "bomb", "rocket", "explosion", "military",
        "army", "troops", "war", "combat", "weapon", "artillery", "drone", "airstrike",
        "tank", "soldier", "battalion", "infantry", "naval", "siege", "shelling",
        "هجوم", "صاروخ", "قصف", "انفجار", "عسكري", "جيش", "قوات", "طائرة", "ضربة",
        "دبابة", "جندي", "حصار", "مدفعية",
    ],
    "political": [
        "government", "president", "minister", "election", "vote", "parliament",
        "treaty", "sanction", "diplomat", "policy", "protest", "demonstration",
        "summit", "ceasefire", "negotiation", "resolution", "ambassador",
        "حكومة", "رئيس", "وزير", "انتخاب", "برلمان", "احتجاج", "مظاهرة",
        "سياسة", "دبلوماسية", "وقف إطلاق النار", "مفاوضات",
    ],
    "humanitarian": [
        "aid", "refugee", "displaced", "humanitarian", "hospital", "medical",
        "food", "water", "shelter", "evacuate", "casualty", "civilian", "injury",
        "death", "killed", "wounded", "rescue", "relief", "corridor",
        "مساعدة", "لاجئ", "نازح", "إنساني", "مستشفى", "طبي", "طعام", "ماء",
        "مدني", "ضحايا", "جرحى", "إخلاء", "إغاثة",
    ],
    "crime": [
        "arrest", "kidnap", "murder", "theft", "drug", "criminal", "crime",
        "shoot", "gang", "trafficking", "smuggle", "detain",
        "اعتقال", "اختطاف", "جريمة", "قتل", "سرقة", "مخدرات", "عصابة",
    ],
    "accident": [
        "accident", "crash", "fire", "flood", "earthquake", "disaster",
        "collapse", "explosion", "storm", "landslide",
        "حادث", "تصادم", "حريق", "فيضان", "زلزال", "كارثة", "انهيار",
    ],
}

# ── Side keywords ──────────────────────────────────────────────────────────────
_RED_KEYWORDS = [
    # English — adversary groups and actions
    "hamas", "al-qassam", "qassam brigades", "islamic jihad", "pij",
    "hezbollah", "hizballah", "al-quds brigades", "aqsa martyrs",
    "lion's den", "resistance fired", "rockets fired toward", "launched rockets",
    "fired rockets", "rockets toward israel", "missiles toward israel",
    "attacked israel", "terror attack", "martyred", "martyrdom operation",
    "anti-tank missile", "infiltration attempt",
    # Arabic — adversary groups and operations
    "حماس", "القسام", "كتائب القسام", "الجهاد الإسلامي", "سرايا القدس",
    "حزب الله", "المقاومة الفلسطينية", "فصائل المقاومة", "إطلاق صواريخ",
    "صواريخ نحو إسرائيل", "قذائف صاروخية", "عملية نوعية", "استشهد",
    "مجاهدين", "حركة حماس", "انطلاق صواريخ", "مسيرات انتحارية",
    "كتائب عز الدين", "قسام",
]

_BLUE_KEYWORDS = [
    # English — Israeli / IDF
    "idf", "israel defense forces", "israeli army", "israeli air force",
    "iaf", "iron dome", "david's sling", "arrow missile", "mossad",
    "shin bet", "shabak", "israel police", "israel struck", "israel launched",
    "israeli strike", "israeli operation", "intercepted", "interception",
    "israel hit", "israeli forces", "israel military", "israel navy",
    "unit 8200", "netanyahu", "idf spokesperson", "idf confirmed",
    "israeli troops entered", "idf operation",
    # Arabic — Israeli forces as described by Arab media
    "الجيش الإسرائيلي", "قوات الاحتلال", "طائرات الاحتلال", "جيش الاحتلال",
    "الاحتلال الإسرائيلي", "القبة الحديدية", "سلاح الجو الإسرائيلي",
    "قوات الجيش", "الموساد", "الشاباك", "الكنيست", "نتنياهو",
    "قوات خاصة إسرائيلية", "اقتحام إسرائيلي", "دبابات إسرائيلية",
]

_NEUTRAL_KEYWORDS = [
    "un ", "unrwa", "unicef", "who ", "icrc", "red cross", "red crescent",
    "hospital", "civilian", "displaced", "aid", "relief", "humanitarian",
    "ceasefire", "negotiation", "diplomatic", "agreement", "peace talks",
    "international community", "media report", "reuters", "al jazeera",
    "journalist", "correspondent", "bbc", "protest", "demonstration",
    "أممي", "أونروا", "هيئة الأمم", "مستشفى", "مدني", "نازح",
    "مساعدات", "وقف إطلاق النار", "مفاوضات", "دبلوماسي", "وكالة",
    "تظاهرة", "احتجاج",
]


def classify_event(title: str, description: str = "") -> tuple[str, float]:
    """Return (category, confidence)."""
    text = f"{title} {description}".lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[category] = score
    if not scores:
        return "other", 0.3
    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = min(0.95, 0.4 + (scores[best] / max(1, total)) * 0.55)
    return best, round(confidence, 2)


def classify_side(title: str, description: str = "") -> tuple[str, float]:
    """
    Return (side, confidence) — one of 'red', 'blue', 'neutral'.

    red     — adversary / hostile actor operations
    blue    — Israeli / IDF operations and statements
    neutral — civilian, humanitarian, political, international, ambiguous
    """
    text = f"{title} {description}".lower()

    red_score  = sum(1 for kw in _RED_KEYWORDS    if kw.lower() in text)
    blue_score = sum(1 for kw in _BLUE_KEYWORDS   if kw.lower() in text)
    neut_score = sum(1 for kw in _NEUTRAL_KEYWORDS if kw.lower() in text)

    total = red_score + blue_score + neut_score

    if total == 0:
        return "neutral", 0.35

    if red_score > blue_score and red_score > neut_score:
        conf = min(0.95, 0.50 + (red_score / total) * 0.45)
        return "red", round(conf, 2)

    if blue_score > red_score and blue_score > neut_score:
        conf = min(0.95, 0.50 + (blue_score / total) * 0.45)
        return "blue", round(conf, 2)

    conf = min(0.85, 0.45 + (neut_score / max(1, total)) * 0.40) if neut_score else 0.45
    return "neutral", round(conf, 2)
