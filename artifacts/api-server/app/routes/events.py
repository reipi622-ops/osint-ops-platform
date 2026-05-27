import math
import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.services.deduplicator import compute_hash

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    base_q = db.query(models.Event).filter(models.Event.is_duplicate == False)

    total = base_q.count()
    today_count = base_q.filter(models.Event.created_at >= today).count()
    week_count = base_q.filter(models.Event.created_at >= week_ago).count()

    category_rows = (
        db.query(models.Event.category, func.count(models.Event.id))
        .filter(models.Event.is_duplicate == False)
        .group_by(models.Event.category)
        .all()
    )
    by_category = [schemas.CategoryCount(category=r[0] or "other", count=r[1]) for r in category_rows]

    source_rows = (
        db.query(models.Event.source_name, func.count(models.Event.id))
        .filter(models.Event.is_duplicate == False, models.Event.source_name.isnot(None))
        .group_by(models.Event.source_name)
        .order_by(func.count(models.Event.id).desc())
        .limit(10)
        .all()
    )
    by_source = [schemas.SourceCount(source_name=r[0] or "Unknown", count=r[1]) for r in source_rows]

    timeline = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_events = (
            base_q.filter(models.Event.created_at >= day, models.Event.created_at < day_end).all()
        )
        cats: dict = {}
        for e in day_events:
            cats[e.category or "other"] = cats.get(e.category or "other", 0) + 1
        timeline.append(schemas.DailyCount(date=day.strftime("%Y-%m-%d"), count=len(day_events), categories=cats))

    return schemas.DashboardStats(
        total_events=total or 0,
        events_today=today_count or 0,
        events_this_week=week_count or 0,
        by_category=by_category,
        by_source=by_source,
        recent_timeline=timeline,
    )


@router.get("", response_model=schemas.EventListResponse)
async def list_events(
    category: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Event).filter(models.Event.is_duplicate == False)

    if category:
        query = query.filter(models.Event.category == category)
    if source_id:
        query = query.filter(models.Event.source_id == source_id)
    if date_from:
        query = query.filter(models.Event.created_at >= date_from)
    if date_to:
        query = query.filter(models.Event.created_at <= date_to)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                models.Event.title.ilike(term),
                models.Event.title_he.ilike(term),
                models.Event.description_he.ilike(term),
                models.Event.location_name.ilike(term),
            )
        )

    if lat is not None and lng is not None and radius_km is not None:
        lat_delta = radius_km / 111.0
        cos_lat = math.cos(math.radians(lat))
        lng_delta = radius_km / (111.0 * max(cos_lat, 0.001))
        query = query.filter(
            and_(
                models.Event.lat.isnot(None),
                models.Event.lng.isnot(None),
                models.Event.lat.between(lat - lat_delta, lat + lat_delta),
                models.Event.lng.between(lng - lng_delta, lng + lng_delta),
            )
        )

    total = query.count()
    items = query.order_by(models.Event.created_at.desc()).offset(offset).limit(limit).all()

    return schemas.EventListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{event_id}", response_model=schemas.EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("", response_model=schemas.EventResponse, status_code=201)
async def create_event(event: schemas.EventInput, db: Session = Depends(get_db)):
    event_hash = compute_hash(event.title, event.description or "")
    existing = db.query(models.Event).filter(models.Event.event_hash == event_hash).first()

    db_event = models.Event(
        **event.model_dump(),
        event_hash=event_hash,
        is_duplicate=existing is not None,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.put("/{event_id}", response_model=schemas.EventResponse)
async def update_event(event_id: int, update: schemas.EventUpdate, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for k, v in update.model_dump(exclude_none=True).items():
        setattr(event, k, v)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
