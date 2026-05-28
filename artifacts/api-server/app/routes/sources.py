import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sources", tags=["sources"])


def _with_count(source: models.Source, db: Session) -> schemas.SourceResponse:
    count = db.query(func.count(models.Event.id)).filter(models.Event.source_id == source.id).scalar() or 0
    resp = schemas.SourceResponse.model_validate(source)
    resp.events_count = count
    return resp


@router.get("", response_model=List[schemas.SourceResponse])
async def list_sources(db: Session = Depends(get_db)):
    sources = db.query(models.Source).order_by(models.Source.name).all()
    return [_with_count(s, db) for s in sources]


@router.post("", response_model=schemas.SourceResponse, status_code=201)
async def create_source(source: schemas.SourceInput, db: Session = Depends(get_db)):
    existing = db.query(models.Source).filter(models.Source.url == source.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source with this URL already exists")
    db_source = models.Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return _with_count(db_source, db)


@router.put("/{source_id}", response_model=schemas.SourceResponse)
async def update_source(source_id: int, update: schemas.SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for k, v in update.model_dump(exclude_none=True).items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)
    return _with_count(source, db)


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()


@router.get("/{source_id}/stats", response_model=schemas.SourceStats)
async def get_source_stats(source_id: int, db: Session = Depends(get_db)):
    """Return detailed reliability and activity statistics for a source."""
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    base = db.query(models.Event).filter(
        models.Event.source_id == source_id,
        models.Event.is_duplicate == False,
    )

    total = base.count()
    if total == 0:
        return schemas.SourceStats(
            source_id=source_id,
            source_name=source.name,
            source_type=source.type,
            total_events=0,
            avg_confidence=0.0,
            avg_propaganda=0.0,
            avg_importance=0.0,
            important_events=0,
            reliability_score=0.0,
            reliability_history=[],
            propaganda_trend=[],
            hourly_activity=[schemas.HourlyActivity(hour=h, count=0) for h in range(24)],
        )

    rows = base.with_entities(
        models.Event.confidence,
        models.Event.propaganda_score,
        models.Event.importance_score,
        models.Event.is_important,
        models.Event.created_at,
    ).all()

    confidences = [float(r.confidence or 0) for r in rows]
    propagandas = [float(r.propaganda_score or 0) for r in rows]
    importances = [float(r.importance_score or 0) for r in rows]
    avg_conf   = round(sum(confidences) / total, 3)
    avg_prop   = round(sum(propagandas) / total, 3)
    avg_imp    = round(sum(importances) / total, 3)
    imp_events = sum(1 for r in rows if r.is_important)

    # Reliability score: weighted composite
    reliability_score = round(
        max(0.0, avg_conf - avg_prop * 0.5) * (1 + min(0.2, imp_events / max(total, 1) * 0.5)),
        3,
    )

    # Fetch event_date for speed computation
    rows_full = base.with_entities(
        models.Event.confidence,
        models.Event.propaganda_score,
        models.Event.importance_score,
        models.Event.is_important,
        models.Event.created_at,
        models.Event.event_date,
    ).all()

    # Daily reliability + propaganda history — last 14 days
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    history = []
    propaganda_trend = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_rows = [r for r in rows_full if r.created_at and day <= r.created_at < day_end]
        n = len(day_rows)
        if n:
            day_conf = round(sum(float(r.confidence or 0) for r in day_rows) / n, 3)
            day_prop = round(sum(float(r.propaganda_score or 0) for r in day_rows) / n, 3)
        else:
            day_conf = 0.0
            day_prop = 0.0
        date_str = day.strftime("%Y-%m-%d")
        history.append(schemas.ReliabilityPoint(
            date=date_str,
            avg_confidence=day_conf,
            avg_propaganda=day_prop,
            event_count=n,
        ))
        propaganda_trend.append(schemas.PropagandaTrend(
            date=date_str,
            avg_propaganda=day_prop,
            event_count=n,
        ))

    # Hourly activity distribution (hour of day 0-23)
    hourly: dict = {h: 0 for h in range(24)}
    for r in rows_full:
        if r.created_at:
            hourly[r.created_at.hour] += 1
    hourly_activity = [schemas.HourlyActivity(hour=h, count=hourly[h]) for h in range(24)]

    # Average time between event_date and scrape (how fast the source reports)
    speed_deltas = []
    for r in rows_full:
        if r.event_date and r.created_at and r.event_date < r.created_at:
            delta = (r.created_at - r.event_date).total_seconds()
            if 0 < delta < 86400 * 7:  # sanity bound: within 7 days
                speed_deltas.append(delta)
    avg_first_report = round(sum(speed_deltas) / len(speed_deltas), 1) if speed_deltas else None

    return schemas.SourceStats(
        source_id=source_id,
        source_name=source.name,
        source_type=source.type,
        total_events=total,
        avg_confidence=avg_conf,
        avg_propaganda=avg_prop,
        avg_importance=avg_imp,
        important_events=imp_events,
        reliability_score=reliability_score,
        reliability_history=history,
        propaganda_trend=propaganda_trend,
        hourly_activity=hourly_activity,
        avg_first_report_seconds=avg_first_report,
    )
