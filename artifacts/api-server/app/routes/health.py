import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.schemas import HealthStatus, SystemMetrics
from app.database import get_db
from app import models

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

_start_time = time.time()


@router.get("/healthz", response_model=HealthStatus)
async def health_check(db: Session = Depends(get_db)):
    """Full health check with system metrics."""
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        cpu = proc.cpu_percent(interval=0.1)
        mem_mb = mem.rss / 1024 / 1024
        mem_pct = psutil.virtual_memory().percent
    except Exception:
        cpu = 0.0
        mem_mb = 0.0
        mem_pct = 0.0

    try:
        from app.services.event_broadcaster import broadcaster
        sse_subs = broadcaster.subscriber_count
    except Exception:
        sse_subs = 0

    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        base_q = db.query(models.Event).filter(models.Event.is_duplicate == False)
        total_events = base_q.count()
        today_events = base_q.filter(models.Event.created_at >= today).count()
        alerts_total = base_q.filter(models.Event.is_important == True).count()
        db_status = "connected"
    except Exception as e:
        logger.warning("Health check DB error: %s", e)
        total_events = 0
        today_events = 0
        alerts_total = 0
        db_status = "error"

    metrics = SystemMetrics(
        cpu_percent=round(cpu, 1),
        memory_mb=round(mem_mb, 1),
        memory_percent=round(mem_pct, 1),
        uptime_seconds=round(time.time() - _start_time, 1),
        sse_subscribers=sse_subs,
        events_total=total_events,
        events_today=today_events,
        alerts_total=alerts_total,
    )

    return HealthStatus(
        status="ok",
        version="2.0.0",
        database=db_status,
        metrics=metrics,
    )
