"""
Pattern detection engine — detects intelligence patterns from the live event stream.

Three detectors run on an in-memory sliding window:
  spike        — >6 events from the same side within 15 minutes
  escalation   — rolling 30-min avg importance score rises >0.2 vs previous 30-min window
  coordinated  — same event (near-dup hash) reported by ≥3 distinct sources within 10 min

Patterns expire after 4 hours and are stored in a bounded deque (max 50).
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_PATTERN_EXPIRY_HOURS = 4
_MAX_PATTERNS = 50
_WINDOW_MAX = 500  # how many recent events to keep in memory

# Each entry: {id, side, importance_score, source_name, event_hash, location_hint, ts}
_event_window: deque = deque(maxlen=_WINDOW_MAX)
_pattern_store: deque = deque(maxlen=_MAX_PATTERNS)


@dataclass
class PatternAlert:
    pattern_type: str           # spike | escalation | coordinated
    severity: str               # low | medium | high | critical
    description: str
    location_hint: Optional[str]
    event_ids: list
    detected_at: datetime
    expires_at: datetime = field(init=False)

    def __post_init__(self) -> None:
        self.expires_at = self.detected_at + timedelta(hours=_PATTERN_EXPIRY_HOURS)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "type": self.pattern_type,
            "severity": self.severity,
            "description": self.description,
            "location_hint": self.location_hint,
            "event_ids": self.event_ids,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


# ── public API ─────────────────────────────────────────────────────────────────

def register_event_for_patterns(
    event_id: int,
    side: str,
    importance_score: float,
    source_name: Optional[str],
    event_hash: str,
    location_hint: Optional[str] = None,
) -> list:
    """
    Register a newly stored event and run all detectors.
    Returns a list of PatternAlert objects triggered (may be empty).
    """
    now = datetime.utcnow()
    _event_window.append({
        "id": event_id,
        "side": side or "neutral",
        "importance_score": float(importance_score or 0),
        "source_name": source_name or "unknown",
        "event_hash": event_hash or "",
        "location_hint": location_hint,
        "ts": now,
    })

    new_patterns: list = []
    new_patterns.extend(_detect_spike(now))
    new_patterns.extend(_detect_escalation(now))
    new_patterns.extend(_detect_coordinated(now))

    for p in new_patterns:
        _pattern_store.append(p)
        logger.info(
            "Pattern detected: %s [%s] — %s",
            p.pattern_type, p.severity, p.description,
        )

    return new_patterns


def get_active_patterns() -> list:
    """Return all non-expired patterns as dicts, most recent first."""
    active = [p for p in _pattern_store if not p.is_expired()]
    active.sort(key=lambda p: p.detected_at, reverse=True)
    return [p.to_dict() for p in active]


# ── helpers ────────────────────────────────────────────────────────────────────

def _recent(now: datetime, minutes: int) -> list:
    cutoff = now - timedelta(minutes=minutes)
    return [e for e in _event_window if e["ts"] >= cutoff]


def _cooldown(pattern_type: str, side_hint: str, seconds: int, now: datetime) -> bool:
    """True if a matching pattern was already raised within the cooldown window."""
    return any(
        p.pattern_type == pattern_type
        and side_hint in p.description
        and not p.is_expired()
        and (now - p.detected_at).total_seconds() < seconds
        for p in _pattern_store
    )


# ── detectors ──────────────────────────────────────────────────────────────────

def _detect_spike(now: datetime) -> list:
    """Spike: >6 events from the same side within 15 min (15-min cooldown per side)."""
    window = _recent(now, 15)
    patterns = []

    for side in ("red", "blue", "neutral"):
        side_events = [e for e in window if e["side"] == side]
        n = len(side_events)
        if n <= 6:
            continue

        side_label = {"red": "Adversary", "blue": "IDF/Blue", "neutral": "Neutral"}[side]
        if _cooldown("spike", side_label, 900, now):
            continue

        severity = "critical" if n >= 15 else "high" if n >= 10 else "medium"
        patterns.append(PatternAlert(
            pattern_type="spike",
            severity=severity,
            description=f"Activity spike: {n} {side_label} events in 15 min",
            location_hint=(side_events[-1].get("location_hint")),
            event_ids=[e["id"] for e in side_events[-12:]],
            detected_at=now,
        ))

    return patterns


def _detect_escalation(now: datetime) -> list:
    """Escalation trend: avg importance score in current 30-min window rose >0.2 vs previous."""
    cutoff_prev   = now - timedelta(minutes=60)
    cutoff_mid    = now - timedelta(minutes=30)
    window_curr   = _recent(now, 30)
    window_prev   = [e for e in _event_window if cutoff_prev <= e["ts"] < cutoff_mid]

    if len(window_curr) < 3 or len(window_prev) < 3:
        return []

    avg_curr = sum(e["importance_score"] for e in window_curr) / len(window_curr)
    avg_prev = sum(e["importance_score"] for e in window_prev) / len(window_prev)
    delta    = avg_curr - avg_prev

    if delta < 0.20:
        return []

    if _cooldown("escalation", "Escalation", 1200, now):
        return []

    severity = "critical" if delta >= 0.40 else "high" if delta >= 0.30 else "medium"
    return [PatternAlert(
        pattern_type="escalation",
        severity=severity,
        description=f"Escalation trend: avg threat score +{delta:.2f} over last 30 min",
        location_hint=None,
        event_ids=[e["id"] for e in window_curr[-8:]],
        detected_at=now,
    )]


def _detect_coordinated(now: datetime) -> list:
    """Coordinated: ≥3 distinct sources report the same near-dup hash within 10 min."""
    window = _recent(now, 10)
    hash_groups: dict = {}
    for e in window:
        h = e["event_hash"]
        if h:
            hash_groups.setdefault(h, []).append(e)

    patterns = []
    for h, events in hash_groups.items():
        unique_sources = {e["source_name"] for e in events}
        if len(unique_sources) < 3:
            continue

        tag = h[:8]
        if _cooldown("coordinated", tag, 600, now):
            continue

        severity = "high" if len(unique_sources) >= 5 else "medium"
        patterns.append(PatternAlert(
            pattern_type="coordinated",
            severity=severity,
            description=f"Coordinated report: {len(unique_sources)} sources confirmed event {tag}…",
            location_hint=events[-1].get("location_hint"),
            event_ids=[e["id"] for e in events],
            detected_at=now,
        ))

    return patterns
