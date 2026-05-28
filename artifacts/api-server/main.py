import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text as sa_text
from app.database import engine
from app import models
from app.routes import health, events, sources, scraper as scraper_router
from app.routes import telegram as telegram_router
from app.services.scraper import initialize_default_sources
from app.services.seed import seed_sample_events
from app.services import telegram_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


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
        ],
    }
    with engine.connect() as conn:
        for table, stmts in table_migrations.items():
            existing = {
                row[1]
                for row in conn.execute(sa_text(f"PRAGMA table_info({table})"))
            }
            for stmt in stmts:
                col = stmt.split("ADD COLUMN")[1].strip().split()[0]
                if col not in existing:
                    conn.execute(sa_text(stmt))
                    conn.commit()
                    logger.info("DB migration: %s.%s added", table, col)


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    _migrate_db()
    initialize_default_sources()
    seed_sample_events()

    # Start Telegram monitor (no-op if TELEGRAM_API_ID/HASH not set)
    await telegram_monitor.init_client()

    logger.info("OSINT Platform API started")
    yield

    await telegram_monitor.disconnect_client()
    logger.info("OSINT Platform API shutting down")


app = FastAPI(
    title="OSINT Platform API",
    version="1.0.0",
    description="OSINT platform for collecting, translating, and analyzing events",
    lifespan=lifespan,
)

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
    return {"message": "OSINT Platform API", "version": "1.0.0"}
