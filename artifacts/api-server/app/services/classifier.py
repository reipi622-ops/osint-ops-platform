"""
Event classifier: returns (category, confidence), (side, side_confidence),
and importance detection.

Side classification (Middle East OSINT context):
  red     — hostile / adversary operations (Hamas, Hezbollah, PIJ, Iran-backed)
  blue    — Israeli / IDF operations and statements
  neutral — civilian, humanitarian, political, international community, unknown

Importance detection:
  Flags high-value tactical events: airstrikes, rockets, casualties, UAVs,
  explosions, IDF statements, Hezbollah activity, etc.
"""

from __future__ import annotations

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "military": [
        "attack", "strike", "missile", "bomb", "rocket", "explosion", "military",
        "army", "troops", "war", "combat", "weapon", "artillery", "drone", "airstrike",
        "tank", "soldier", "battalion", "infantry", "naval", "siege", "shelling",
        "intercept", "target", "operation", "raid", "infiltration", "ambush",
        "هجوم", "صاروخ", "قصف", "انفجار", "عسكري", "جيش", "قوات", "طائرة", "ضربة",
        "دبابة", "جندي", "حصار", "مدفعية", "غارة", "مسيرة", "كمين", "اشتباك",
        "قذيفة", "قصف جوي", "ضربة جوية", "رشقة", "وابل",
    ],
    "political": [
        "government", "president", "minister", "election", "vote", "parliament",
        "treaty", "sanction", "diplomat", "policy", "protest", "demonstration",
        "summit", "ceasefire", "negotiation", "resolution", "ambassador",
        "حكومة", "رئيس", "وزير", "انتخاب", "برلمان", "احتجاج", "مظاهرة",
        "سياسة", "دبلوماسية", "وقف إطلاق النار", "مفاوضات", "قرار", "سفير",
    ],
    "humanitarian": [
        "aid", "refugee", "displaced", "humanitarian", "hospital", "medical",
        "food", "water", "shelter", "evacuate", "casualty", "civilian", "injury",
        "death", "killed", "wounded", "rescue", "relief", "corridor",
        "مساعدة", "لاجئ", "نازح", "إنساني", "مستشفى", "طبي", "طعام", "ماء",
        "مدني", "ضحايا", "جرحى", "إخلاء", "إغاثة", "شهيد", "استشهد",
    ],
    "crime": [
        "arrest", "kidnap", "murder", "theft", "drug", "criminal", "crime",
        "shoot", "gang", "trafficking", "smuggle", "detain",
        "اعتقال", "اختطاف", "جريمة", "قتل", "سرقة", "مخدرات", "عصابة",
    ],
    "accident": [
        "accident", "crash", "fire", "flood", "earthquake", "disaster",
        "collapse", "storm", "landslide",
        "حادث", "تصادم", "حريق", "فيضان", "زلزال", "كارثة", "انهيار",
    ],
}

# ── Side keywords ──────────────────────────────────────────────────────────────
_RED_KEYWORDS = [
    "hamas", "al-qassam", "qassam", "islamic jihad", "pij", "al-quds brigades",
    "hezbollah", "hizballah", "hizbullah", "al-quds force", "aqsa martyrs",
    "resistance fired", "rockets fired", "launched rockets", "fired rockets",
    "rockets toward israel", "missiles toward israel", "attacked israel",
    "terror attack", "martyred", "martyrdom operation", "anti-tank missile",
    "infiltration attempt", "resistance operation", "axis of resistance",
    "حماس", "القسام", "كتائب القسام", "الجهاد الإسلامي", "سرايا القدس",
    "حزب الله", "المقاومة الإسلامية", "المقاومة الفلسطينية", "فصائل المقاومة",
    "إطلاق صواريخ", "صواريخ نحو إسرائيل", "قذائف صاروخية", "عملية نوعية",
    "استشهد", "مجاهدين", "حركة حماس", "انطلاق صواريخ", "مسيرات انتحارية",
    "كتائب عز الدين", "قسام", "قوة الرضوان", "محور المقاومة",
    "صاروخ مضاد للدروع", "كمين للاحتلال", "هجوم صاروخي",
]

_BLUE_KEYWORDS = [
    "idf", "israel defense forces", "israeli army", "israeli air force",
    "iaf", "iron dome", "david's sling", "arrow missile", "mossad",
    "shin bet", "shabak", "israel police", "israel struck", "israel launched",
    "israeli strike", "israeli operation", "intercepted by", "interception",
    "israel hit", "israeli forces", "israel military", "israel navy",
    "unit 8200", "netanyahu", "idf spokesperson", "idf confirmed",
    "idf announced", "idf says", "idf troops", "idf operation",
    "israeli troops entered", "home front command", "red alert israel",
    "الجيش الإسرائيلي", "قوات الاحتلال", "طائرات الاحتلال", "جيش الاحتلال",
    "الاحتلال الإسرائيلي", "القبة الحديدية", "سلاح الجو الإسرائيلي",
    "الموساد", "الشاباك", "الكنيست", "نتنياهو", "غالانت", "هرتسي هليفي",
    "قوات خاصة إسرائيلية", "اقتحام إسرائيلي", "دبابات إسرائيلية",
    "المتحدث العسكري الإسرائيلي", "بيان إسرائيلي", "تصريح إسرائيلي",
    "الجبهة الداخلية", "صفارات الإنذار في إسرائيل",
]

_NEUTRAL_KEYWORDS = [
    "un ", "unrwa", "unicef", "who ", "icrc", "red cross", "red crescent",
    "hospital", "civilian", "displaced", "aid", "relief", "humanitarian",
    "ceasefire", "negotiation", "diplomatic", "agreement", "peace talks",
    "international community", "reuters", "al jazeera", "bbc", "afp",
    "journalist", "correspondent", "protest", "demonstration",
    "أممي", "أونروا", "هيئة الأمم", "مستشفى", "مدني", "نازح",
    "مساعدات", "وقف إطلاق النار", "مفاوضات", "دبلوماسي", "وكالة",
    "تظاهرة", "احتجاج", "إعلامي", "مراسل", "صليب الأحمر",
]

# ── Importance rules ───────────────────────────────────────────────────────────
# Each rule: (tag, weight, keywords)
# weight: contribution to importance_score
# is_important when score >= 0.5
_IMPORTANCE_RULES: list[tuple[str, float, list[str]]] = [
    ("rockets", 0.70, [
        "rocket", "rockets", "missile", "missiles", "katyusha", "mortar shells",
        "barrage of", "salvo", "fired rockets", "launched rockets",
        "صاروخ", "صواريخ", "كاتيوشا", "رشقة صاروخية", "إطلاق صواريخ",
        "قذائف صاروخية", "وابل من الصواريخ", "قصف صاروخي",
    ]),
    ("uav", 0.60, [
        "drone", "uav", "uavs", "unmanned aerial", "quadcopter", "suicide drone",
        "مسيرة", "مسيرات", "طائرة مسيرة", "طائرات مسيرة", "درون", "كوادكوبتر",
        "مسيرة انتحارية", "مسيرة مفخخة",
    ]),
    ("airstrike", 0.70, [
        "airstrike", "air strike", "air raid", "bombing run", "warplane",
        "f-16", "f-35", "apache",
        "غارة", "غارات", "ضربة جوية", "ضربات جوية", "قصف جوي",
        "طيران حربي", "غارة جوية", "غارة حربية", "غارات متواصلة",
        "طائرات الحرب", "قصف الطيران",
    ]),
    ("casualties", 0.80, [
        "killed", "dead", "deaths", "martyred", "wounded", "casualties",
        "fatalities", "injured", "victim", "victims",
        "استشهد", "شهيد", "شهداء", "قتيل", "قتلى", "جريح", "جرحى",
        "ضحايا", "اغتيل", "مقتل", "وفاة", "سقط قتيلا",
    ]),
    ("explosion", 0.50, [
        "explosion", "explosions", "blast", "detonation", "blew up",
        "انفجار", "انفجارات", "تفجير", "دوي انفجار", "صوت انفجار",
        "لغم", "عبوة ناسفة",
    ]),
    ("heavy_bombardment", 0.70, [
        "heavy shelling", "intense bombardment", "massive barrage",
        "dozens of rockets", "hundreds of rockets", "intense fire",
        "قصف مكثف", "قصف عنيف", "قصف متواصل", "عشرات القذائف",
        "مئات الصواريخ", "قصف مستمر", "قصف متقطع", "قصف مدفعي",
    ]),
    ("idf_statement", 0.55, [
        "idf confirms", "idf says", "idf spokesperson", "idf announced",
        "idf operation", "idf targeted",
        "أعلن الجيش الإسرائيلي", "المتحدث العسكري الإسرائيلي",
        "الناطق بلسان الجيش", "بيان الجيش الإسرائيلي",
    ]),
    ("hezbollah", 0.55, [
        "hezbollah", "hizballah", "hizbullah", "islamic resistance",
        "حزب الله", "المقاومة الإسلامية", "قوة الرضوان",
    ]),
    ("warning_alert", 0.55, [
        "red alert", "warning siren", "sirens activated", "home front command",
        "صافرات إنذار", "إنذار", "دفاع مدني", "صفارات الإنذار",
        "تحذير", "إشعار تحذير", "تنبيه",
    ]),
]

_IMPORTANCE_THRESHOLD = 0.50


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


def detect_importance(title: str, description: str = "") -> tuple[bool, float, str]:
    """
    Detect whether this event is tactically significant.

    Returns:
        is_important  — True if importance_score >= threshold
        importance_score — float 0..1 (higher = more important)
        importance_tags  — comma-separated matched rule tags (e.g. "airstrike,casualties")
    """
    text = f"{title} {description}".lower()
    matched_tags: list[str] = []
    score = 0.0

    for tag, weight, keywords in _IMPORTANCE_RULES:
        if any(kw.lower() in text for kw in keywords):
            matched_tags.append(tag)
            score += weight

    score = min(1.0, score)
    is_important = score >= _IMPORTANCE_THRESHOLD

    return is_important, round(score, 2), ",".join(matched_tags)
