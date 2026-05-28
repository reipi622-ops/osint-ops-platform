"""
Deduplication utilities.

Two-layer approach:
1. Exact dedup — SHA-256 hash of normalized text (prevents same message stored twice).
2. Near-dedup  — Jaccard similarity on word sets against a short in-memory rolling window.
   When a near-duplicate is found the ORIGINAL event gets a confirmation credit — the new
   source is logged as a corroborating witness, raising its confidence_level.
"""
from __future__ import annotations

import hashlib
import re
from collections import deque
from typing import Optional

# Rolling window of recent (normalized_text, event_id) for near-dedup
_RECENT_WINDOW: deque[tuple[str, int]] = deque(maxlen=300)

# Similarity threshold for near-duplicate flagging
_NEAR_DUP_THRESHOLD = 0.72


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[\U0001F300-\U0001FFFF\u2600-\u27BF]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", "", text)
    return text.strip()


def compute_hash(title: str, description: str = "") -> str:
    normalized = normalize_text(f"{title} {description[:200]}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def is_near_duplicate(text: str) -> tuple[bool, Optional[int]]:
    """
    Check whether a very similar event is already in the recent window.
    Returns (is_near_dup, existing_event_id).
    Does NOT modify the window — call register_event() after a successful store.
    """
    normalized = normalize_text(text)
    words = set(normalized.split())
    if len(words) < 4:
        return False, None

    for cached_text, cached_id in _RECENT_WINDOW:
        cached_words = set(cached_text.split())
        if _jaccard(words, cached_words) >= _NEAR_DUP_THRESHOLD:
            return True, cached_id

    return False, None


def register_event(text: str, event_id: int) -> None:
    """Add a newly stored event to the rolling near-dedup window."""
    _RECENT_WINDOW.appendleft((normalize_text(text), event_id))


def credit_confirmation(event_id: int, confirming_source: str) -> None:
    """
    Update the original event's confirmation_count and confirming_sources in the DB.
    Called when a near-duplicate is detected so the original gets a credibility boost.
    Runs synchronously (called from a thread).
    """
    try:
        from app.database import SessionLocal
        from app import models
        from app.services.classifier import compute_confidence_level

        db = SessionLocal()
        try:
            ev = db.query(models.Event).filter(models.Event.id == event_id).first()
            if not ev:
                return

            ev.confirmation_count = (ev.confirmation_count or 0) + 1

            # Append source if not already credited
            existing = (ev.confirming_sources or "").split(",")
            existing = [s for s in existing if s]
            if confirming_source not in existing:
                existing.append(confirming_source)
            ev.confirming_sources = ",".join(existing)

            # Re-derive confidence level now that we have more confirmation
            ev.confidence_level = compute_confidence_level(
                ev.confidence or 0.5,
                ev.importance_score or 0.0,
                ev.confirmation_count,
                bool(ev.has_media),
                ev.propaganda_score or 0.0,
            )

            try:
                db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()
    except Exception:
        pass  # never let confirmation bookkeeping crash the pipeline
