import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routes import health, events, sources, scraper as scraper_router
from app.routes import telegram as telegram_router
from app.services.scraper import initialize_default_sources
from app.services.seed import seed_sample_events
from app.services import telegram_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
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
