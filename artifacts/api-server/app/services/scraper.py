import logging
import threading
from datetime import datetime
from typing import List, Tuple

import feedparser

from app.database import SessionLocal
from app import models, schemas
from app.services.classifier import (
    classify_event,
    classify_side,
    detect_importance,
    detect_propaganda,
    compute_confidence_level,
    compute_escalation_level,
    detect_text_has_media_keywords,
)
from app.services.deduplicator import compute_hash
from app.services.geolocator import extract_location
from app.services.translator import translate_text

logger = logging.getLogger(__name__)

_state: dict = {
    "is_running": False,
    "last_run_at": None,
    "last_run_events": 0,
    "last_run_errors": [],
}
_lock = threading.Lock()

DEFAULT_SOURCES = [
    {"name": "Al Jazeera Arabic", "type": "rss", "url": "https://www.aljazeera.net/xml/atom/1.xml"},
    {"name": "BBC Arabic", "type": "rss", "url": "https://feeds.bbci.co.uk/arabic/rss.xml"},
    {"name": "Reuters World", "type": "rss", "url": "https://feeds.reuters.com/reuters/worldNews"},
    {"name": "Ynet News", "type": "rss", "url": "https://www.ynet.co.il/Integration/StoryRss1854.xml"},
    {"name": "Times of Israel", "type": "rss", "url": "https://www.timesofisrael.com/feed/"},
]


def get_scraper_status(db) -> schemas.ScraperStatus:
    with _lock:
        sources_count = db.query(models.Source).filter(models.Source.is_active == True).count()
        return schemas.ScraperStatus(
            is_running=_state["is_running"],
            last_run_at=_state["last_run_at"],
            last_run_events=_state["last_run_events"],
            last_run_errors=list(_state["last_run_errors"]),
            sources_count=sources_count,
        )


def initialize_default_sources() -> None:
    db = SessionLocal()
    try:
        if db.query(models.Source).count() == 0:
            for src in DEFAULT_SOURCES:
                db.add(models.Source(**src))
            db.commit()
            logger.info("Initialized %d default sources", len(DEFAULT_SOURCES))
    finally:
        db.close()


def _is_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in text)


def _process_entry(entry, source: models.Source, db) -> bool:
    title_orig = (getattr(entry, "title", "") or "").strip()
    desc_orig = (
        getattr(entry, "summary", "")
        or getattr(entry, "description", "")
        or ""
    ).strip()
    url = getattr(entry, "link", "") or ""

    if not title_orig:
        return False

    event_hash = compute_hash(title_orig, desc_orig)
    if db.query(models.Event).filter(models.Event.event_hash == event_hash).first():
        return False

    is_ar = _is_arabic(title_orig)
    original_lang = "ar" if is_ar else "en"

    title_he = translate_text(title_orig, original_lang, "he") if is_ar else title_orig
    desc_he = translate_text(desc_orig[:1000], original_lang, "he") if (is_ar and desc_orig) else desc_orig

    category, confidence = classify_event(title_orig, desc_orig)
    side, _side_conf = classify_side(title_orig, desc_orig)
    combined = f"{title_orig} {desc_orig}"
    is_important, importance_score, importance_tags = detect_importance(title_orig, desc_orig)
    propaganda_score = detect_propaganda(combined)
    has_media = detect_text_has_media_keywords(combined)
    confidence_level = compute_confidence_level(
        confidence=confidence,
        importance_score=importance_score,
        confirmation_count=0,
        has_media=has_media,
        propaganda_score=propaganda_score,
    )
    escalation_level = compute_escalation_level(
        importance_score=importance_score,
        confidence=confidence,
        confirmation_count=0,
        confidence_level=confidence_level,
        threat_tags=importance_tags or "",
    )
    location_name, lat, lng = extract_location(combined)

    published = getattr(entry, "published_parsed", None)
    event_date = datetime(*published[:6]) if published else datetime.utcnow()

    event = models.Event(
        title=title_orig,
        title_he=title_he,
        description=desc_orig[:2000] or None,
        description_he=desc_he[:2000] if desc_he else None,
        category=category,
        side=side,
        confidence=confidence,
        is_important=is_important,
        importance_score=importance_score,
        importance_tags=importance_tags or None,
        propaganda_score=propaganda_score,
        has_media=has_media,
        confidence_level=confidence_level,
        escalation_level=escalation_level,
        confirmation_count=0,
        source_id=source.id,
        source_name=source.name,
        source_url=url,
        location_name=location_name,
        lat=lat,
        lng=lng,
        original_lang=original_lang,
        raw_text=title_orig,
        event_hash=event_hash,
        is_duplicate=False,
        event_date=event_date,
    )
    db.add(event)
    db.flush()  # get event.id before commit

    # Register in pattern engine (non-blocking)
    try:
        from app.services.pattern_engine import register_event_for_patterns
        register_event_for_patterns(
            event_id=event.id,
            side=side,
            importance_score=importance_score,
            source_name=source.name,
            event_hash=event_hash,
            location_hint=location_name,
        )
    except Exception as pe:
        logger.debug("Pattern engine registration skipped: %s", pe)

    return True


def _scrape_source(source: models.Source, db) -> Tuple[int, List[str]]:
    added = 0
    errors: List[str] = []
    try:
        feed = feedparser.parse(source.url)
        if not feed.entries:
            errors.append(f"{source.name}: no entries found")
            return 0, errors

        for entry in feed.entries[:15]:
            try:
                if _process_entry(entry, source, db):
                    db.commit()
                    added += 1
            except Exception as e:
                db.rollback()
                errors.append(f"{source.name}: {str(e)[:80]}")

        source.last_scraped_at = datetime.utcnow()
        db.commit()
        logger.info("Scraped %d events from %s", added, source.name)
    except Exception as e:
        errors.append(f"{source.name}: {str(e)[:80]}")
        logger.error("Failed to scrape %s: %s", source.name, e)
    return added, errors


def run_scraper_background() -> None:
    with _lock:
        if _state["is_running"]:
            return
        _state["is_running"] = True
        _state["last_run_errors"] = []
        _state["last_run_events"] = 0

    db = SessionLocal()
    total_added = 0
    total_errors: List[str] = []
    try:
        sources = db.query(models.Source).filter(models.Source.is_active == True).all()
        for source in sources:
            n, errs = _scrape_source(source, db)
            total_added += n
            total_errors.extend(errs)
    except Exception as e:
        total_errors.append(str(e))
        logger.error("Scraper error: %s", e)
    finally:
        db.close()
        with _lock:
            _state["is_running"] = False
            _state["last_run_at"] = datetime.utcnow()
            _state["last_run_events"] = total_added
            _state["last_run_errors"] = total_errors
        logger.info("Scraper finished: %d events, %d errors", total_added, len(total_errors))
