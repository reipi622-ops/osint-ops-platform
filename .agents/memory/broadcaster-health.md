---
name: Broadcaster health + eviction
description: SSE EventBroadcaster class design, health endpoint, and eviction behaviour.
---

## Rule
`artifacts/api-server/app/services/event_broadcaster.py` — module-level singleton `broadcaster`.

Key constants:
- `QUEUE_CAP = 200` — per-subscriber asyncio.Queue maxsize
- `WARN_DEPTH = 150` — 75% threshold; WARNING logged before queue fills

Counters maintained across process lifetime:
- `_total_delivered` — cumulative successful deliveries
- `_total_evictions` — cumulative forced disconnects (queue full)

Health endpoint:
```
GET /api/events/stream/health
```
Returns: `active_subscribers`, `queue_cap`, `warn_depth`, `total_delivered`, `total_evictions`, `queue_depths` (list), `max_queue_depth`.

**Why:** Without eviction counters it was impossible to know if slow clients were silently losing events. Health endpoint lets ops detect backpressure before it becomes an outage.

**How to apply:** After any burst test, check `total_evictions == 0`. If > 0, the slow-client path fired — investigate client reconnect rate or increase `QUEUE_CAP`.

## Verified behaviour (2026-05-28)
- 5 concurrent SSE clients, burst fetch across 6 channels: `total_evictions = 0`.
- `total_delivered = 5` for that session (5 SSE frames pushed).
