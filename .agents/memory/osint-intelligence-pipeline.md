---
name: Backend intelligence pipeline
description: How events flow through the OSINT classification/dedup/broadcast pipeline and what the confidence levels mean
---

## Pipeline order
`telegram_monitor.py` / RSS scraper → `classifier.py` → `deduplicator.py` → DB insert → `event_broadcaster.py` SSE

## Confidence levels
`low` / `medium` / `high` / `verified` — computed by `compute_confidence_level()` in `classifier.py`.

- **verified**: confirmation_count ≥ 2 AND confidence ≥ 0.60 AND propaganda_score < 0.40
- **high**: confidence ≥ 0.70 OR (confirmation_count ≥ 1 AND has_media)
- **medium**: confidence ≥ 0.45
- **low**: everything else

## Near-duplicate confirmation flow
`is_near_duplicate()` returns `(True, event_id)` → caller must call `credit_confirmation(event_id, source)` to update `confirmation_count`, `confirming_sources`, and recompute `confidence_level` on the original event. Do NOT silently drop near-dups.

## New DB columns (added via `_migrate_db()`)
`confirmation_count`, `confirming_sources`, `has_media`, `propaganda_score`, `confidence_level` on the `events` table.

**Why:** Silently dropping near-dups threw away cross-source confirmation signal. Crediting confirmations is what elevates an event to "verified".
