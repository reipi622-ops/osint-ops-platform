import logging
import threading
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.services.scraper import run_scraper_background, get_scraper_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.get("/status", response_model=schemas.ScraperStatus)
async def scraper_status(db: Session = Depends(get_db)):
    return get_scraper_status(db)


@router.post("/trigger", response_model=schemas.ScraperStatus)
async def trigger_scraper(db: Session = Depends(get_db)):
    status = get_scraper_status(db)
    if not status.is_running:
        thread = threading.Thread(target=run_scraper_background, daemon=True)
        thread.start()
        logger.info("Scraper triggered in background thread")
    return get_scraper_status(db)
