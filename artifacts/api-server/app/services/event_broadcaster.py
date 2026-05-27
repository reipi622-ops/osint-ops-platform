"""
SSE event broadcaster — pub/sub using per-client asyncio Queues.
New events from any source (Telegram, RSS scraper) are pushed to all
connected SSE clients without polling.
"""
import asyncio
import logging
from typing import Set

logger = logging.getLogger(__name__)


class EventBroadcaster:
    def __init__(self) -> None:
        self._queues: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues.add(q)
        logger.debug("SSE client subscribed, total=%d", len(self._queues))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)
        logger.debug("SSE client unsubscribed, total=%d", len(self._queues))

    async def broadcast(self, payload: dict) -> None:
        if not self._queues:
            return
        dead: Set[asyncio.Queue] = set()
        for q in self._queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.add(q)
        for q in dead:
            self._queues.discard(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


# Module-level singleton shared across the whole process
broadcaster = EventBroadcaster()
