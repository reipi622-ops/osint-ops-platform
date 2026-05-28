"""
Deduplication utilities.

Two-layer approach:
1. Exact dedup — SHA-256 hash of normalized text (already in place, prevents
   the same message being stored twice).
2. Near-dedup  — Jaccard similarity on word sets against a short in-memory
   rolling window of recent events. Catches the same incident reported by
   multiple channels with slightly different wording.
"""
from __future__ import annotations

import hashlib
import re
from collections import deque
from typing import Optional

# Rolling window of recent (normalized_text, event_id) for near-dedup
# Keeps the last 300 events — fast, no DB hit needed
_RECENT_WINDOW: deque[tuple[str, int]] = deque(maxlen=300)

# Similarity threshold for near-duplicate flagging
_NEAR_DUP_THRESHOLD = 0.72


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    # Strip emoji and non-text symbols
    text = re.sub(r"[\U0001F300-\U0001FFFF\u2600-\u27BF]", "", text)
    text = re.sub(r"\s+", " ", text)
    # Keep Arabic letters, Latin letters, digits, Arabic diacritics
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
        # Too short to do meaningful similarity — skip near-dedup
        return False, None

    for cached_text, cached_id in _RECENT_WINDOW:
        cached_words = set(cached_text.split())
        if _jaccard(words, cached_words) >= _NEAR_DUP_THRESHOLD:
            return True, cached_id

    return False, None


def register_event(text: str, event_id: int) -> None:
    """Add a newly stored event to the rolling near-dedup window."""
    _RECENT_WINDOW.appendleft((normalize_text(text), event_id))
