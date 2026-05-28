"""Unit tests for the event classifier."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.classifier import (
    classify_event,
    classify_side,
    detect_importance,
    detect_propaganda,
    compute_confidence_level,
    detect_text_has_media_keywords,
)


# ── classify_event ─────────────────────────────────────────────────────────────

def test_classify_event_military():
    cat, conf = classify_event("Israeli airstrike hit a missile depot in Gaza")
    assert cat == "military"
    assert conf > 0.4


def test_classify_event_humanitarian():
    cat, conf = classify_event("Aid convoy evacuating wounded civilians from hospital")
    assert cat == "humanitarian"
    assert conf > 0.4


def test_classify_event_political():
    cat, conf = classify_event("Prime minister called for ceasefire negotiations in parliament")
    assert cat == "political"
    assert conf > 0.4


def test_classify_event_unknown():
    cat, conf = classify_event("Hello world")
    assert cat == "other"
    assert conf == 0.3


def test_classify_event_arabic_military():
    cat, conf = classify_event("قصف جوي على منطقة شمال غزة أسفر عن انفجار")
    assert cat == "military"
    assert conf > 0.4


# ── classify_side ─────────────────────────────────────────────────────────────

def test_classify_side_red_hamas():
    side, conf = classify_side("Hamas al-Qassam brigades fired rockets toward Israel")
    assert side == "red"
    assert conf >= 0.5


def test_classify_side_blue_idf():
    side, conf = classify_side("IDF spokesperson confirmed Israeli air force struck Hezbollah positions")
    assert side == "blue"
    assert conf >= 0.5


def test_classify_side_neutral():
    side, conf = classify_side("UNRWA says aid convoy reached the hospital")
    assert side == "neutral"


def test_classify_side_default():
    side, conf = classify_side("Something completely unrelated")
    assert side == "neutral"
    assert conf < 0.5


# ── detect_importance ─────────────────────────────────────────────────────────

def test_detect_importance_rockets():
    is_imp, score, tags = detect_importance("Barrage of rockets fired toward northern Israel")
    assert is_imp
    assert score >= 0.5
    assert "rockets" in tags


def test_detect_importance_casualties():
    is_imp, score, tags = detect_importance("Three soldiers killed in ambush, five wounded")
    assert is_imp
    assert score >= 0.5
    assert "casualties" in tags


def test_detect_importance_airstrike():
    is_imp, score, tags = detect_importance("Israeli warplane carried out an airstrike on targets")
    assert is_imp
    assert "airstrike" in tags


def test_detect_importance_low():
    is_imp, score, tags = detect_importance("Local market opened today in the city center")
    assert not is_imp
    assert score < 0.5


def test_detect_importance_arabic_rockets():
    is_imp, score, tags = detect_importance("إطلاق رشقة صاروخية نحو إسرائيل")
    assert is_imp
    assert "rockets" in tags


# ── detect_propaganda ─────────────────────────────────────────────────────────

def test_detect_propaganda_genocide():
    score = detect_propaganda("This is genocide and ethnic cleansing by the Zionist regime")
    assert score > 0.5


def test_detect_propaganda_massacre():
    score = detect_propaganda("The savage massacre and barbaric slaughter must stop")
    assert score > 0.3


def test_detect_propaganda_neutral():
    score = detect_propaganda("IDF forces entered northern Gaza on a military operation")
    assert score < 0.4


def test_detect_propaganda_exclamation_boost():
    score = detect_propaganda("War crimes!!! Genocide!!! Extermination!!!")
    assert score > 0.5


def test_detect_propaganda_arabic():
    score = detect_propaganda("إبادة جماعية وتطهير عرقي بيد الكيان الصهيوني")
    assert score > 0.5


def test_detect_propaganda_caps_boost():
    score = detect_propaganda("THIS IS GENOCIDE AND ETHNIC CLEANSING AND WAR CRIMES")
    assert score > 0.5


# ── compute_confidence_level ──────────────────────────────────────────────────

def test_confidence_level_low_default():
    level = compute_confidence_level(0.3, 0.0, 0, False, 0.0)
    assert level == "low"


def test_confidence_level_medium():
    level = compute_confidence_level(0.55, 0.3, 0, False, 0.1)
    assert level == "medium"


def test_confidence_level_high_single_source():
    level = compute_confidence_level(0.80, 0.5, 0, False, 0.1)
    assert level == "high"


def test_confidence_level_high_confirmed():
    level = compute_confidence_level(0.60, 0.5, 1, False, 0.1)
    assert level == "high"


def test_confidence_level_verified():
    level = compute_confidence_level(0.70, 0.6, 2, False, 0.2)
    assert level == "verified"


def test_confidence_level_propaganda_kills():
    level = compute_confidence_level(0.90, 0.9, 5, True, 0.65)
    assert level == "low"


def test_confidence_level_media_boost():
    # 0.65 + 0.10 = 0.75 → high
    level = compute_confidence_level(0.65, 0.5, 0, True, 0.1)
    assert level == "high"


# ── detect_text_has_media_keywords ────────────────────────────────────────────

def test_media_keywords_video():
    assert detect_text_has_media_keywords("Watch the video footage of the airstrike")


def test_media_keywords_arabic():
    assert detect_text_has_media_keywords("شاهد الفيديو من الموقع")


def test_media_keywords_none():
    assert not detect_text_has_media_keywords("Forces moved into the area at dawn")
