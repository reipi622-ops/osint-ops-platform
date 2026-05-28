---
name: SQLite WAL + pragma pattern
description: How WAL mode and session pragmas are applied in this project's SQLAlchemy setup, and the raw-connection caveat.
---

## Rule
WAL mode and all session-scoped pragmas are set in `artifacts/api-server/app/database.py` via a SQLAlchemy `connect` event listener:

```python
@sa_event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA cache_size=-8000")
    cur.execute("PRAGMA busy_timeout=10000")
    cur.close()
```

`journal_mode=WAL` persists in the database file itself once set (survives process restarts). The others are session-scoped and must be re-applied per connection.

**Why:** Raw `sqlite3.connect()` calls (diagnostic scripts, tests) bypass the SQLAlchemy pool and will NOT have these pragmas unless they set them explicitly. This caused misleading validation results where synchronous/FK/cache showed defaults in scripts.

**How to apply:** Any new diagnostic or migration script that opens SQLite directly must set at minimum `PRAGMA busy_timeout=10000` to avoid `OperationalError: database is locked` during concurrent API operation.

## Verified behaviour (2026-05-28)
- `osint.db-wal` and `osint.db-shm` confirmed present after restart.
- `PRAGMA wal_checkpoint(PASSIVE)` returned `(0, 134, 134)` — all WAL frames synced.
- 30 concurrent HTTP→SQLAlchemy ops: 0 errors, avg 664 ms, max 859 ms.
