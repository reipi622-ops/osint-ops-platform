import asyncio
import json
import math
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.services.deduplicator import compute_hash
from app.services.event_broadcaster import broadcaster

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


@router.get("/stream")
async def events_stream(request: Request):
    """
    Server-Sent Events stream. Clients receive a 'new_event' message for every
    event processed by Telegram monitor or RSS scraper, plus a heartbeat every
    20 s to keep the connection alive through proxies.
    """
    q = broadcaster.subscribe()

    async def generate():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=20.0)
                    data = json.dumps(payload, default=str)
                    yield f"event: new_event\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/alerts", response_model=schemas.EventListResponse)
async def list_alerts(
    side: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """Return the most recent important/high-priority events."""
    query = (
        db.query(models.Event)
        .filter(models.Event.is_duplicate == False, models.Event.is_important == True)
    )
    if side:
        query = query.filter(models.Event.side == side)
    total = query.count()
    items = (
        query
        .order_by(models.Event.importance_score.desc(), models.Event.created_at.desc())
        .limit(limit)
        .all()
    )
    return schemas.EventListResponse(items=items, total=total, offset=0, limit=limit)


@router.get("/timeline", response_model=schemas.EventTimelineResponse)
async def get_timeline(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Return hourly event counts (total + by side) for the last N hours."""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=hours)

    events = (
        db.query(models.Event.created_at, models.Event.side)
        .filter(
            models.Event.is_duplicate == False,
            models.Event.created_at >= cutoff,
        )
        .all()
    )

    # Bucket by hour
    buckets: dict[str, dict[str, int]] = {}
    for created_at, side in events:
        if created_at is None:
            continue
        # truncate to hour
        h = created_at.replace(minute=0, second=0, microsecond=0)
        key = h.strftime("%Y-%m-%dT%H:00:00")
        if key not in buckets:
            buckets[key] = {"total": 0, "red": 0, "blue": 0, "neutral": 0}
        s = side or "neutral"
        buckets[key]["total"] += 1
        buckets[key][s] = buckets[key].get(s, 0) + 1

    # Fill in all hours (even empty ones) for a continuous timeline
    result: list[schemas.HourlyCount] = []
    for i in range(hours - 1, -1, -1):
        h = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        key = h.strftime("%Y-%m-%dT%H:00:00")
        b = buckets.get(key, {"total": 0, "red": 0, "blue": 0, "neutral": 0})
        result.append(schemas.HourlyCount(
            hour=key,
            total=b["total"],
            red=b.get("red", 0),
            blue=b.get("blue", 0),
            neutral=b.get("neutral", 0),
        ))

    return schemas.EventTimelineResponse(hours=result, window_hours=hours)


@router.get("", response_model=schemas.EventListResponse)
async def list_events(
    category: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None),
    source_name: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    has_location: Optional[bool] = Query(None),
    is_important: Optional[bool] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Event).filter(models.Event.is_duplicate == False)

    if category:
        query = query.filter(models.Event.category == category)
    if side:
        query = query.filter(models.Event.side == side)
    if source_name:
        query = query.filter(models.Event.source_name.ilike(f"%{source_name}%"))
    if has_location is True:
        query = query.filter(models.Event.lat.isnot(None), models.Event.lng.isnot(None))
    if has_location is False:
        query = query.filter(or_(models.Event.lat.is_(None), models.Event.lng.is_(None)))
    if is_important is True:
        query = query.filter(models.Event.is_important == True)
    if is_important is False:
        query = query.filter(models.Event.is_important == False)
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

    from app.schemas import EventResponse
    from pydantic import TypeAdapter
    payload = TypeAdapter(EventResponse).validate_python(db_event).model_dump(mode="json")
    await broadcaster.broadcast(payload)

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
