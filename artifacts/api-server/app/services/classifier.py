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


def classify_event(title: str, description: str = "") -> tuple[str, float]:
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
