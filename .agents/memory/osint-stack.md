---
name: OSINT Stack
description: Key quirks and decisions for the OSINT platform (FastAPI+SQLite+Telethon + React/Vite+Leaflet+Recharts)
---

## Backend

- API server runs via `bash artifacts/api-server/run.sh` on port 8080, path `/api`
- `limit` Query param was capped at `le=200` in both `/events` and `/events/alerts` routes — raised to `le=500` to support the map view requesting 300 events
- `importance_tags` stored as comma-separated string in SQLite; parse with `str.split(",")` client-side
- `reliability_score` on SourceResponse is a Pydantic `@computed_field @property` — no DB column
- DB migration pattern: PRAGMA table_info → check existing columns → ALTER TABLE ADD COLUMN per missing column (in `main.py` startup)
- near-dedup: in-memory deque (maxlen=300), Jaccard similarity; call `register_event(text, id)` after storing
- Telegram monitor runs in a thread; call `detect_importance` and `is_near_duplicate` inside `_process_message_sync`

## Frontend

- `SIDE_LABELS` kept for Hebrew/Arabic display; `SIDE_LABELS_EN` for English UI labels
- EventDrawer: slide-in from right, fixed positioning, z-index 1200 over backdrop at 1100
- Recharts `BarChart` with `stackId="a"` stacks red/blue/neutral bars per hour bucket
- `/events/alerts` and `/events/timeline` endpoints added; hooks: `useListAlerts`, `useGetEventsTimeline`
- `getListAlertsQueryKey` / `getGetEventsTimelineQueryKey` needed when passing custom query options

**Why:** FastAPI validates Query params strictly — exceeding `le` gives 422 not a graceful truncation.
