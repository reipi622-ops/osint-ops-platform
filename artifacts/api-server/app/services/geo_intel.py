"""
Geographic intelligence: clusters events by location and identifies hot zones.

Algorithm:
  - Round each event's lat/lng to the nearest 0.2° grid cell (~22 km resolution).
  - Aggregate all non-duplicate events with coordinates from the past 24 hours.
  - Any cell with ≥4 events is declared a "hot zone".
  - Threat level is derived from avg importance score and event count.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

_GRID_RESOLUTION  = 0.2   # degrees — ≈22 km per cell
_HOTZONE_MIN      = 4     # min events for a cell to become a hot zone
_WINDOW_HOURS     = 24    # look-back window
_CELL_RADIUS_KM   = 22.0  # approximate radius in km for a 0.2° cell


@dataclass
class GeoCluster:
    grid_lat: float
    grid_lng: float
    center_lat: float
    center_lng: float
    radius_km: float
    event_count: int
    dominant_side: str
    last_event_at: Optional[datetime]
    threat_level: str    # low | medium | high | critical
    event_ids: list
    is_hotzone: bool

    def to_dict(self) -> dict:
        return {
            "grid_lat": self.grid_lat,
            "grid_lng": self.grid_lng,
            "center_lat": self.center_lat,
            "center_lng": self.center_lng,
            "radius_km": self.radius_km,
            "event_count": self.event_count,
            "dominant_side": self.dominant_side,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "threat_level": self.threat_level,
            "event_ids": self.event_ids,
            "is_hotzone": self.is_hotzone,
        }


# ── public API ──────────────────────────────────────────────────────────────────

def compute_clusters(db) -> list:
    """Return all geographic clusters (sorted by threat, then event count desc)."""
    from app import models

    cutoff = datetime.utcnow() - timedelta(hours=_WINDOW_HOURS)
    events = (
        db.query(models.Event)
        .filter(
            models.Event.is_duplicate == False,
            models.Event.lat.isnot(None),
            models.Event.lng.isnot(None),
            models.Event.created_at >= cutoff,
        )
        .all()
    )

    # Group into grid cells
    grid: dict = {}
    for e in events:
        cell_lat = round(e.lat / _GRID_RESOLUTION) * _GRID_RESOLUTION
        cell_lng = round(e.lng / _GRID_RESOLUTION) * _GRID_RESOLUTION
        key = (round(cell_lat, 4), round(cell_lng, 4))
        grid.setdefault(key, []).append(e)

    _THREAT_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    clusters = []

    for (cell_lat, cell_lng), cell_events in grid.items():
        n = len(cell_events)
        lats = [e.lat for e in cell_events]
        lngs = [e.lng for e in cell_events]
        center_lat = round(sum(lats) / n, 4)
        center_lng = round(sum(lngs) / n, 4)

        # Dominant side
        side_counts: dict = {}
        for e in cell_events:
            s = e.side or "neutral"
            side_counts[s] = side_counts.get(s, 0) + 1
        dominant_side = max(side_counts, key=lambda k: side_counts[k])

        # Most recent event timestamp
        last_event_at = max(
            (e.created_at for e in cell_events if e.created_at),
            default=None,
        )

        # Threat level from avg importance score + count
        avg_imp = sum(float(e.importance_score or 0) for e in cell_events) / n
        if avg_imp >= 0.70 or n >= 15:
            threat_level = "critical"
        elif avg_imp >= 0.50 or n >= 8:
            threat_level = "high"
        elif avg_imp >= 0.30 or n >= 4:
            threat_level = "medium"
        else:
            threat_level = "low"

        clusters.append(GeoCluster(
            grid_lat=cell_lat,
            grid_lng=cell_lng,
            center_lat=center_lat,
            center_lng=center_lng,
            radius_km=_CELL_RADIUS_KM,
            event_count=n,
            dominant_side=dominant_side,
            last_event_at=last_event_at,
            threat_level=threat_level,
            event_ids=[e.id for e in cell_events],
            is_hotzone=(n >= _HOTZONE_MIN),
        ))

    clusters.sort(key=lambda c: (_THREAT_ORDER.get(c.threat_level, 3), -c.event_count))
    return clusters


def get_hotzones(db) -> list:
    """Return only clusters qualifying as hot zones (≥4 events in last 24 h)."""
    return [c for c in compute_clusters(db) if c.is_hotzone]
