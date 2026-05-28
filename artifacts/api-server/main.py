import os
import time
import logging
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text as sa_text
from app.database import engine
from app import models
from app.routes import health, events, sources, scraper as scraper_router
from app.routes import telegram as telegram_router
from app.services.scraper import initialize_default_sources
from app.services.seed import seed_sample_events
from app.services import telegram_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Rate limiting middleware ───────────────────────────────────────────────────

_rate_buckets: dict = defaultdict(lambda: {"count": 0, "reset_at": 0.0})

# Path-specific limits: (calls_per_period, period_seconds)
_RATE_LIMITS: list[tuple[str, int, int]] = [
    ("/api/telegram/auth", 5, 60),   # auth endpoints: 5/min
    ("/api/scraper",       10, 60),  # manual scraper: 10/min
]
_DEFAULT_RATE = (200, 60)  # 200 req/min for everything else


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # SSE streams are long-lived — exempt from rate limiting
        if request.url.path.endswith("/stream"):
            return await call_next(request)

        ip = (request.client.host if request.client else "unknown") or "unknown"
        path = request.url.path

        calls, period = _DEFAULT_RATE
        for prefix, c, p in _RATE_LIMITS:
            if path.startswith(prefix):
                calls, period = c, p
                break

        bucket_key = f"{ip}:{path[:40]}"
        now = time.monotonic()
        bucket = _rate_buckets[bucket_key]

        if now > bucket["reset_at"]:
            bucket["count"] = 0
            bucket["reset_at"] = now + period

        bucket["count"] += 1
        if bucket["count"] > calls:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please slow down."},
                status_code=429,
                headers={"Retry-After": str(int(bucket["reset_at"] - now))},
            )

        return await call_next(request)


# ── Request logging middleware ─────────────────────────────────────────────────

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.monotonic()
        response = await call_next(request)
        ms = (time.monotonic() - t0) * 1000
        # Skip noisy SSE and health spam
        skip = ("/stream", "/healthz")
        if not any(request.url.path.endswith(s) for s in skip):
            logger.info(
                "HTTP %s %s → %d  %.1f ms",
                request.method, request.url.path, response.status_code, ms,
            )
        return response


# ── DB migrations ──────────────────────────────────────────────────────────────

def _migrate_db() -> None:
    """Add new columns to existing tables without dropping data (SQLite-safe)."""
    table_migrations: dict[str, list[str]] = {
        "telegram_channels": [
            "ALTER TABLE telegram_channels ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE telegram_channels ADD COLUMN approved_at DATETIME",
            "ALTER TABLE telegram_channels ADD COLUMN is_public_verified INTEGER NOT NULL DEFAULT 0",
        ],
        "events": [
            "ALTER TABLE events ADD COLUMN side TEXT NOT NULL DEFAULT 'neutral'",
            "ALTER TABLE events ADD COLUMN is_important INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE events ADD COLUMN importance_score REAL DEFAULT 0.0",
            "ALTER TABLE events ADD COLUMN importance_tags TEXT",
            # Intelligence reliability fields (v2)
            "ALTER TABLE events ADD COLUMN confirmation_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE events ADD COLUMN confirming_sources TEXT",
            "ALTER TABLE events ADD COLUMN has_media INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE events ADD COLUMN propaganda_score REAL DEFAULT 0.0",
            "ALTER TABLE events ADD COLUMN confidence_level TEXT NOT NULL DEFAULT 'low'",
        ],
    }
    with engine.connect() as conn:
        for table, stmts in table_migrations.items():
            try:
                existing = {
                    row[1]
                    for row in conn.execute(sa_text(f"PRAGMA table_info({table})"))
                }
            except Exception:
                existing = set()
            for stmt in stmts:
                col = stmt.split("ADD COLUMN")[1].strip().split()[0]
                if col not in existing:
                    try:
                        conn.execute(sa_text(stmt))
                        conn.commit()
                        logger.info("DB migration: %s.%s added", table, col)
                    except Exception as exc:
                        logger.warning("DB migration skipped %s.%s: %s", table, col, exc)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    _migrate_db()
    initialize_default_sources()
    seed_sample_events()

    await telegram_monitor.init_client()
    logger.info("OSINT Platform API v2 started")
    yield

    await telegram_monitor.disconnect_client()
    logger.info("OSINT Platform API shutting down")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OSINT Platform API",
    version="2.0.0",
    description="OSINT platform for collecting, translating, and analyzing events",
    lifespan=lifespan,
)

app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(scraper_router.router, prefix="/api")
app.include_router(telegram_router.router, prefix="/api")


@app.get("/api")
async def root():
    return {"message": "OSINT Platform API", "version": "2.0.0"}
