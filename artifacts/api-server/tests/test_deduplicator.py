"""Unit tests for the event deduplicator."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Reset the dedup window before each test by reloading or clearing it
from app.services import deduplicator


def _clear_window():
    deduplicator._RECENT_WINDOW.clear()


# ── normalize_text ────────────────────────────────────────────────────────────

def test_normalize_lowercase():
    assert deduplicator.normalize_text("HELLO World") == "hello world"


def test_normalize_strips_emoji():
    result = deduplicator.normalize_text("Fire 🔥 in the city")
    assert "🔥" not in result
    assert "fire" in result


def test_normalize_whitespace():
    assert deduplicator.normalize_text("  hello   world  ") == "hello world"


def test_normalize_arabic_preserved():
    text = "قصف على المدينة"
    result = deduplicator.normalize_text(text)
    assert "قصف" in result
    assert "المدينة" in result


# ── compute_hash ──────────────────────────────────────────────────────────────

def test_hash_deterministic():
    h1 = deduplicator.compute_hash("Rockets fired at Israel", "from Gaza")
    h2 = deduplicator.compute_hash("Rockets fired at Israel", "from Gaza")
    assert h1 == h2


def test_hash_different_for_different_text():
    h1 = deduplicator.compute_hash("Event A", "")
    h2 = deduplicator.compute_hash("Event B", "")
    assert h1 != h2


def test_hash_length_16():
    h = deduplicator.compute_hash("Some event title", "Some description")
    assert len(h) == 16


def test_hash_ignores_excess_description():
    # Only first 200 chars of description are used
    desc_short = "x" * 200
    desc_long = "x" * 500
    h1 = deduplicator.compute_hash("title", desc_short)
    h2 = deduplicator.compute_hash("title", desc_long)
    assert h1 == h2


# ── is_near_duplicate ─────────────────────────────────────────────────────────

def test_near_dup_same_text():
    _clear_window()
    deduplicator.register_event("rockets fired toward northern israel from gaza", 1)
    is_dup, eid = deduplicator.is_near_duplicate("rockets fired toward northern israel from gaza")
    assert is_dup
    assert eid == 1


def test_near_dup_slightly_different():
    _clear_window()
    # These two share 10/12 words → Jaccard ≈ 0.83, well above the 0.72 threshold
    original = "IDF targeted Hezbollah weapons depot in northern Gaza killing five militants"
    variant  = "IDF targeted Hezbollah weapons depot in northern Gaza five militants killed"
    deduplicator.register_event(original, 42)
    is_dup, eid = deduplicator.is_near_duplicate(variant)
    assert is_dup
    assert eid == 42


def test_near_dup_completely_different():
    _clear_window()
    deduplicator.register_event("Rockets fired from Gaza toward Ashkelon city", 10)
    is_dup, eid = deduplicator.is_near_duplicate("UN peacekeepers arrived in Beirut for diplomatic talks")
    assert not is_dup
    assert eid is None


def test_near_dup_short_text_skipped():
    _clear_window()
    short = "short text"
    deduplicator.register_event(short, 99)
    is_dup, eid = deduplicator.is_near_duplicate(short)
    # 2 words < 4 minimum — near-dedup skipped
    assert not is_dup


def test_near_dup_does_not_modify_window():
    _clear_window()
    deduplicator.register_event("event one two three four five words", 5)
    size_before = len(deduplicator._RECENT_WINDOW)
    deduplicator.is_near_duplicate("event one two three four five words")
    assert len(deduplicator._RECENT_WINDOW) == size_before


# ── register_event ────────────────────────────────────────────────────────────

def test_register_adds_to_window():
    _clear_window()
    deduplicator.register_event("unique event text for registration test", 77)
    assert len(deduplicator._RECENT_WINDOW) == 1
    assert deduplicator._RECENT_WINDOW[0][1] == 77


def test_register_newest_first():
    _clear_window()
    deduplicator.register_event("first event in the window for ordering", 1)
    deduplicator.register_event("second event in the window for ordering", 2)
    # appendleft — newest is index 0
    assert deduplicator._RECENT_WINDOW[0][1] == 2
    assert deduplicator._RECENT_WINDOW[1][1] == 1


def test_window_maxlen():
    _clear_window()
    for i in range(305):
        deduplicator.register_event(f"event number {i} with some extra filler words", i)
    assert len(deduplicator._RECENT_WINDOW) == 300
