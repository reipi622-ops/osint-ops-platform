"""
Event classifier: returns (category, confidence), (side, side_confidence),
importance detection, propaganda detection, and confidence level.

Side classification (Middle East OSINT context):
  red     — hostile / adversary operations (Hamas, Hezbollah, PIJ, Iran-backed)
  blue    — Israeli / IDF operations and statements
  neutral — civilian, humanitarian, political, international community, unknown

Confidence levels:
  verified — confirmed by multiple independent sources, high confidence, no propaganda
  high     — single strong source OR multi-source confirmation
  medium   — moderate confidence, minimal propaganda
  low      — default; weak signals or high propaganda risk
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
    ("infiltration", 0.65, [
        "infiltration", "infiltrated", "crossed the border", "breached the fence",
        "ground incursion", "crossed into", "anti-tank ambush", "cell entered",
        "تسلل", "اختراق", "تجاوز الحدود", "اقتحام بري", "خلية تسللت",
        "عبر الحدود", "اقتحمت",
    ]),
    ("interception", 0.60, [
        "intercepted", "interception", "iron dome", "david's sling", "arrow",
        "anti-missile", "missile defense", "shot down", "air defense",
        "اعتراض", "تم اعتراض", "القبة الحديدية", "دفاع جوي",
        "منظومة دفاع", "أسقطت", "صاروخ اعتراضي",
    ]),
    ("artillery", 0.65, [
        "artillery", "tank shell", "mortar", "howitzer", "field gun", "shelling",
        "cannon", "tank fire", "artillery barrage", "tank battalion",
        "مدفعية", "قذيفة مدفعية", "هاون", "دبابة", "مدفع", "قصف مدفعي",
        "رشق مدفعي", "طلقة مدفعية", "قذائف الهاون",
    ]),
    ("evacuation", 0.55, [
        "evacuation", "evacuated", "forced to flee", "mass displacement",
        "ordered to leave", "emergency evacuation", "civilians evacuating",
        "إخلاء", "أُجبروا على الفرار", "نزوح جماعي", "أُمروا بالمغادرة",
        "إخلاء فوري", "إخلاء قسري", "هجرة قسرية",
    ]),
    ("cyber", 0.65, [
        "cyber attack", "cyberattack", "hacked", "hacking", "ddos", "malware",
        "ransomware", "power grid attack", "infrastructure attack", "data breach",
        "هجوم إلكتروني", "اختراق إلكتروني", "قرصنة", "هجوم سيبراني",
        "فيروس", "برمجيات خبيثة",
    ]),
]

_IMPORTANCE_THRESHOLD = 0.50

# ── Propaganda / bias detection ────────────────────────────────────────────────
# Each entry: (weight, keywords)
# Total score > 0.5 → high propaganda risk
_PROPAGANDA_RULES: list[tuple[float, list[str]]] = [
    (0.40, [
        # Genocide / extermination framing
        "genocide", "extermination", "ethnic cleansing", "annihilation",
        "إبادة جماعية", "إبادة", "تطهير عرقي",
    ]),
    (0.35, [
        # Massacre / atrocity maximalism
        "massacre", "slaughter", "butcher", "barbaric", "savage attack",
        "مجزرة", "مذبحة", "ذبح", "جريمة حرب", "همجية",
    ]),
    (0.30, [
        # Dehumanization
        "zionist entity", "zionist regime", "occupying entity", "settler colonialism",
        "الكيان الصهيوني", "العدو الصهيوني", "المحتل الصهيوني",
        "الكيان المحتل", "المستوطنين الصهاينة",
    ]),
    (0.25, [
        # Extreme calls to action / incitement
        "must be destroyed", "wipe out", "death to", "will be eliminated",
        "يجب إبادة", "الموت لـ", "سيُمحى", "ستُدمر",
    ]),
    (0.20, [
        # Emotional manipulation superlatives
        "unprecedented atrocity", "worst crime in history", "criminal occupation",
        "أشد جرائم التاريخ", "جريمة لا مثيل لها", "الاحتلال الإجرامي",
    ]),
    (0.15, [
        # Martyrdom glorification used as propaganda
        "glorious martyrdom", "heroic sacrifice", "freedom fighters",
        "استشهاد مجيد", "تضحية بطولية", "المجاهدون الأبطال",
    ]),
]

# ── Media evidence keywords (boosts confidence) ────────────────────────────────
_MEDIA_CONFIDENCE_KEYWORDS = [
    "photo", "photos", "video", "footage", "clip", "image", "images",
    "screenshot", "recorded", "camera", "livestream",
    "صورة", "صور", "فيديو", "مقطع", "تسجيل", "كاميرا", "لقطة",
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
    """Return (side, confidence) — one of 'red', 'blue', 'neutral'."""
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
    Returns (is_important, importance_score, importance_tags_csv).
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


def detect_propaganda(text: str) -> float:
    """
    Analyse text for propaganda / extreme bias indicators.
    Returns a score 0.0 (neutral) → 1.0 (heavy propaganda).
    """
    lowered = text.lower()
    score = 0.0

    for weight, keywords in _PROPAGANDA_RULES:
        if any(kw.lower() in lowered for kw in keywords):
            score += weight

    # Bonus: excessive exclamation marks → emotional manipulation
    exclamation_count = text.count("!")
    if exclamation_count >= 3:
        score += min(0.20, exclamation_count * 0.04)

    # Bonus: ALL CAPS words (3+ letters, 3+ occurrences) → shouting / hysteria
    caps_words = [w for w in text.split() if len(w) >= 3 and w.isupper() and w.isalpha()]
    if len(caps_words) >= 3:
        score += min(0.15, len(caps_words) * 0.03)

    return round(min(1.0, score), 3)


def compute_escalation_level(
    importance_score: float,
    confidence: float,
    confirmation_count: int,
    confidence_level: str,
    threat_tags: str = "",
) -> str:
    """
    Compute operational escalation level from multiple intelligence signals.

    critical — mass-casualty / verified multi-source high-threat event
    high     — confirmed important event OR high-confidence strike/attack
    medium   — any notable event with some corroboration
    low      — default; routine or unconfirmed
    """
    tags = {t.strip() for t in threat_tags.split(",") if t.strip()}
    high_threat = {"rockets", "airstrike", "casualties", "infiltration", "artillery", "interception", "cyber"}
    has_high_threat = bool(tags & high_threat)

    # CRITICAL
    if importance_score >= 0.90:
        return "critical"
    if confidence_level == "verified" and importance_score >= 0.65 and has_high_threat:
        return "critical"
    if confirmation_count >= 2 and importance_score >= 0.75:
        return "critical"

    # HIGH
    if importance_score >= 0.60 and confidence_level in ("high", "verified"):
        return "high"
    if importance_score >= 0.70 and confidence >= 0.65:
        return "high"
    if confirmation_count >= 1 and importance_score >= 0.50:
        return "high"

    # MEDIUM
    if importance_score >= 0.40:
        return "medium"
    if confidence_level in ("medium", "high", "verified") and importance_score >= 0.20:
        return "medium"

    return "low"


def detect_text_has_media_keywords(text: str) -> bool:
    """True if the text references media evidence (photo / video / footage)."""
    lowered = text.lower()
    return any(kw in lowered for kw in _MEDIA_CONFIDENCE_KEYWORDS)


def compute_confidence_level(
    confidence: float,
    importance_score: float,
    confirmation_count: int,
    has_media: bool,
    propaganda_score: float,
) -> str:
    """
    Derive an intelligence confidence level from multiple signals.

    verified — 2+ independent sources confirm, confidence ≥ 0.60, low propaganda
    high     — strong single source (≥0.75) OR confirmed once (≥0.55)
    medium   — moderate confidence (≥0.45), low propaganda
    low      — default
    """
    # Media evidence boosts effective confidence
    eff = confidence + (0.10 if has_media else 0.0)

    # Heavy propaganda kills credibility regardless of other signals
    if propaganda_score >= 0.60:
        return "low"

    # VERIFIED: multi-source confirmation + adequate confidence
    if confirmation_count >= 2 and eff >= 0.60 and propaganda_score < 0.40:
        return "verified"

    # HIGH: very confident single source OR confirmed once
    if eff >= 0.75 and propaganda_score < 0.50:
        return "high"
    if confirmation_count >= 1 and eff >= 0.55 and propaganda_score < 0.50:
        return "high"

    # MEDIUM: moderate confidence
    if eff >= 0.45 and propaganda_score < 0.70:
        return "medium"

    return "low"
