# OSINT Platform — Stability & Reliability Report

**Date:** 2026-05-28  
**Scope:** Production-style validation — WAL mode, broadcaster hardening, burst traffic, integrity tests  
**DB at snapshot:** 216 events · 11 sources · 0 duplicates

---

## 1. Database Layer

### 1.1 WAL Mode

| Check | Result |
|---|---|
| `PRAGMA journal_mode` | **wal** ✅ |
| `osint.db-wal` file exists | ✅ (540 KB, active) |
| `osint.db-shm` file exists | ✅ (32 KB) |
| WAL checkpoint (PASSIVE) | `(0, 134, 134)` — all frames synced |

WAL mode applied via SQLAlchemy `connect` event listener in `database.py`. Also configured:

| Pragma | Value | Reason |
|---|---|---|
| `journal_mode` | `WAL` | Concurrent readers don't block writer |
| `synchronous` | `NORMAL` | Safe + faster than FULL (only risks last WAL segment on power loss) |
| `foreign_keys` | `ON` | Referential integrity enforced |
| `cache_size` | `-8000` (8 MB) | Reduces I/O for repeated scans |
| `busy_timeout` | `10 000 ms` | Threads wait 10 s before raising `OperationalError: database is locked` |

> **Note:** These are session-scoped pragmas applied to SQLAlchemy pool connections only.  
> Raw `sqlite3.connect()` callers (e.g. diagnostic scripts) must set them independently.

### 1.2 Concurrency Benchmark

**Via HTTP → SQLAlchemy → SQLite (realistic API load):**

| Metric | Result |
|---|---|
| Concurrent requests | 30 |
| Wall time | 863 ms |
| Avg latency | 664 ms |
| Min latency | 232 ms |
| Max latency | 859 ms |
| Errors | **0** |

**30 raw `sqlite3` threads (worst-case direct access):**

| Metric | Result |
|---|---|
| Errors | 0 |
| Avg | 2 380 ms |
| Max | 7 496 ms |

The raw-thread numbers reflect SQLite's write-lock serialisation when bypassing  
the connection pool. Normal API operation via SQLAlchemy stays under 860 ms  
at 30-connection burst saturation.

### 1.3 Event Integrity

| Check | Count | Status |
|---|---|---|
| Total events | 216 | — |
| Unique `event_hash` values | 216 | ✅ |
| `is_duplicate = 1` rows | 0 | ✅ |
| `event_hash IS NULL` | 0 | ✅ |

**Concurrent duplicate-insert stress test:**  
Same channel fetched 4 times simultaneously (2 pairs, channels 2 & 4).  
- Events before: 215 · Events after: 215  
- New rows inserted: **0** — dedup held under concurrent load ✅

---

## 2. SSE / Broadcaster

### 2.1 Broadcaster Class (`event_broadcaster.py`)

| Feature | Status |
|---|---|
| Per-client `asyncio.Queue(maxsize=200)` | ✅ |
| WARN_DEPTH at 75 % (150 items) | ✅ |
| WARNING log on backpressure | ✅ |
| WARNING log on client eviction | ✅ |
| `_total_delivered` counter | ✅ |
| `_total_evictions` counter | ✅ |
| `.health()` method | ✅ |

### 2.2 Health Endpoint

```
GET /api/events/stream/health
```

Sample response (idle):
```json
{
  "active_subscribers": 0,
  "queue_cap": 200,
  "warn_depth": 150,
  "total_delivered": 5,
  "total_evictions": 0,
  "queue_depths": [],
  "max_queue_depth": 0
}
```

### 2.3 Reconnect & Multi-Client Test

| Test | Result |
|---|---|
| 5 concurrent SSE clients, handshake received | **5 / 5** ✅ |
| `_sse_type: connected` on all clients | ✅ |
| New event frames delivered consistently | ✅ |
| `total_evictions` after burst | **0** ✅ |
| Heartbeat every 5 s (no-data periods) | ✅ |

### 2.4 Frontend SSE Guard (`use-live-events.ts`)

| Guard | Implementation |
|---|---|
| Stale connection null-check before `es.close()` | `esRef.current = null` before close |
| Dedup via `seenIdsRef` Set | ✅ |
| State cap at 50 live events | `[ev, ...prev].slice(0, 50)` |
| Browser log on connect/disconnect | ✅ |

---

## 3. Burst Traffic

### 3.1 Channel Burst (all 6 channels simultaneous `test-fetch`)

| Channel | Handle | Fetched |
|---|---|---|
| 2 | @newssil | 10 |
| 3 | @nabatiehlb | 8 |
| 4 | @bintjbeilnews | 7 |
| 5 | @nabatiehchannel | 9 |
| 6 | @raknetooooo | 8 |
| 7 | @qudsn | 10 |

**Total messages fetched: 52** across 6 channels simultaneously.  
All processed, classified, geolocated, and stored without error.

### 3.2 Processing Latency (per channel, sequential in earlier burst)

| Channel | Latency | Note |
|---|---|---|
| @newssil | 0.83 s | ✅ Fast |
| @qudsn | 0.74 s | ✅ Fast |
| @bintjbeilnews | 8.70 s | AI pipeline bottleneck |
| @nabatiehlb | 12.37 s | AI pipeline bottleneck |
| @nabatiehchannel | 12.39 s | AI pipeline bottleneck |
| @raknetooooo | 16.17 s | AI pipeline bottleneck — longest |

**Root cause:** AI processing (Arabic→Hebrew translation + classification) is  
sequential per message within each channel. Channels are processed in parallel  
threads but individual messages within a channel are synchronous.  
**Mitigation path:** async AI call batching (not yet implemented).

### 3.3 Memory Under Burst

| State | RSS |
|---|---|
| Baseline (idle) | 29 MB |
| After 6-channel simultaneous burst | 29 MB |
| Delta | **+0 MB** ✅ |

No memory leak detected across burst cycles.

---

## 4. Frontend

### 4.1 Map View (`map-view.tsx`)

| Item | Status |
|---|---|
| API fetch limit | 300 events |
| Live events merged via `useMemo` | ✅ |
| **Marker render cap** | **500** (added this session) |
| Heatmap layer | Uses `mappedEvents` (capped) |
| `HeatmapLayer` canvas repaint | Safe at ≤ 500 markers |

At current scale (132 mapped events) the cap is not reached.  
At 500+ geocoded events, only the most recent 500 render.

### 4.2 Live Intercepts Hook

| Check | Simulation result |
|---|---|
| 250 rapid events → state size | **50** (cap holds) ✅ |
| 200 events with 100 duplicates → stored | **100** (dedup holds) ✅ |
| All React keys unique | ✅ |
| Latest event always at index 0 | ✅ |

### 4.3 Typecheck

```
pnpm --filter @workspace/osint-app run typecheck
```
**Result: clean — no errors** ✅

---

## 5. Risk Register

| # | Risk | Severity | Status |
|---|---|---|---|
| R1 | SQLite concurrent write serialisation under very high load (>50 writers) | Medium | Accepted — WAL + busy_timeout mitigates for current scale |
| R2 | AI processing latency (up to 16 s/channel) creates event delivery lag | Medium | Known — single-threaded AI per channel |
| R3 | No SSE event history — reconnecting clients miss events during gap | Low | Known — clients re-fetch via REST on reconnect |
| R4 | No auth on `/api/events/stream` — any network client can subscribe | Low | Accepted for internal deployment |
| R5 | Telegram session file stored in plaintext on disk | Low | Accepted — read by Telethon only |
| R6 | No rate limit on `POST /telegram/channels/{id}/test-fetch` | Low | Internal tooling only |
| R7 | Map markers uncapped above 500 geocoded events (addressed) | Low | **Mitigated** — 500 cap added |

---

## 6. Summary

| Area | Pass / Total | Notes |
|---|---|---|
| WAL mode enabled | ✅ | Confirmed via file + PRAGMA |
| Pragma health | ✅ | Set on all SQLAlchemy connections |
| 30 concurrent HTTP ops | 30 / 30 ✅ | 0 errors, avg 664 ms |
| 0 duplicate events | ✅ | 216 events, all unique hashes |
| Concurrent dedup stress | ✅ | 4 simultaneous fetches, 0 new rows |
| SSE multi-client | 5 / 5 ✅ | 0 evictions |
| Memory under burst | ✅ | +0 MB delta |
| Frontend typecheck | ✅ | Clean |
| Broadcaster health endpoint | ✅ | `/api/events/stream/health` |
| Map marker cap | ✅ | 500 hard limit |

**Overall status: STABLE** — ready for sustained monitoring use.
