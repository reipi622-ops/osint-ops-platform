"""
SSE event broadcaster — pub/sub using per-client asyncio Queues.

New events from any source (Telegram, RSS scraper) are pushed to all
connected SSE clients without polling.

Reliability notes:
  - Each subscriber gets an independent asyncio.Queue(maxsize=QUEUE_CAP).
  - If a client's queue is full (slow consumer) it is forcibly evicted and
    a WARNING is logged so ops can tune QUEUE_CAP or client reconnect logic.
  - WARN_DEPTH threshold triggers a WARNING before the queue fills, giving
    early visibility into backpressure.
  - _total_evictions tracks cumulative forced disconnects since process start.
"""
import asyncio
import logging
from typing import Set

logger = logging.getLogger(__name__)

QUEUE_CAP: int = 200
WARN_DEPTH: int = int(QUEUE_CAP * 0.75)  # warn at 75 % full = 150 items


class EventBroadcaster:
    def __init__(self) -> None:
        self._queues: Set[asyncio.Queue] = set()
        self._total_evictions: int = 0
        self._total_delivered: int = 0

    # ── subscription lifecycle ─────────────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_CAP)
        self._queues.add(q)
        logger.info("SSE subscriber connected (active=%d)", len(self._queues))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)
        logger.info("SSE subscriber disconnected (active=%d)", len(self._queues))

    # ── broadcast ─────────────────────────────────────────────────────────────

    async def broadcast(self, payload: dict) -> None:
        if not self._queues:
            logger.debug("SSE broadcast: no subscribers (event_id=%s)", payload.get("id"))
            return

        dead: Set[asyncio.Queue] = set()
        delivered = 0

        for q in self._queues:
            depth = q.qsize()
            if depth >= WARN_DEPTH:
                logger.warning(
                    "SSE backpressure: queue depth %d/%d (event_id=%s) "
                    "— slow or unresponsive client",
                    depth, QUEUE_CAP, payload.get("id"),
                )
            try:
                q.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:
                dead.add(q)

        for q in dead:
            self._queues.discard(q)
            self._total_evictions += 1
            logger.warning(
                "SSE: evicted slow/dead subscriber — queue was full "
                "(cap=%d, total_evictions=%d, active=%d, event_id=%s)",
                QUEUE_CAP, self._total_evictions, len(self._queues), payload.get("id"),
            )

        self._total_delivered += delivered

        logger.info(
            "SSE broadcast: delivered=%d evicted=%d active=%d (event_id=%s)",
            delivered, len(dead), len(self._queues), payload.get("id"),
        )

    # ── health ────────────────────────────────────────────────────────────────

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)

    @property
    def total_evictions(self) -> int:
        return self._total_evictions

    def health(self) -> dict:
        depths = [q.qsize() for q in self._queues]
        return {
            "active_subscribers": len(self._queues),
            "queue_cap": QUEUE_CAP,
            "warn_depth": WARN_DEPTH,
            "total_delivered": self._total_delivered,
            "total_evictions": self._total_evictions,
            "queue_depths": depths,
            "max_queue_depth": max(depths, default=0),
        }


# Module-level singleton shared across the whole process
broadcaster = EventBroadcaster()
