"""
Telegram admin routes:
  Auth:     GET/POST /telegram/auth/status|request-code|verify-code|logout
  Channels: GET/POST/PATCH/DELETE /telegram/channels[/{id}]
  SSE:      GET /events/stream   (lives in events router for cleaner path)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services import telegram_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/auth/status", response_model=schemas.TelegramAuthStatus)
async def auth_status():
    s = telegram_monitor.get_status()
    return schemas.TelegramAuthStatus(
        configured=s["configured"],
        connected=s["connected"],
        authorized=s["authorized"],
        phone=s["phone"],
        monitoring=s["monitoring"],
        channels_active=s["channels_active"],
        messages_processed=s["messages_processed"],
        last_message_at=s["last_message_at"],
        error=s["error"],
    )


@router.post("/auth/request-code")
async def request_code(body: schemas.TelegramCodeRequest):
    if not telegram_monitor.get_status()["configured"]:
        raise HTTPException(
            status_code=503,
            detail="Telegram is not configured. Set TELEGRAM_API_ID and TELEGRAM_API_HASH secrets.",
        )
    try:
        await telegram_monitor.request_code(body.phone)
        return {"message": f"Code sent to {body.phone}", "phone": body.phone}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/auth/verify-code")
async def verify_code(body: schemas.TelegramVerifyRequest):
    try:
        await telegram_monitor.verify_code(body.phone, body.code, body.password)
        return {"message": "Authentication successful", "authorized": True}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/auth/logout")
async def logout():
    await telegram_monitor.logout()
    return {"message": "Logged out"}


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[schemas.TelegramChannelResponse])
async def list_channels(db: Session = Depends(get_db)):
    return db.query(models.TelegramChannel).order_by(models.TelegramChannel.created_at.desc()).all()


@router.post("/channels", response_model=schemas.TelegramChannelResponse, status_code=201)
async def add_channel(body: schemas.TelegramChannelInput, db: Session = Depends(get_db)):
    import re
    username = re.sub(r"^https?://t\.me/", "", body.username.strip()).lstrip("@")
    existing = db.query(models.TelegramChannel).filter(
        models.TelegramChannel.username.ilike(username)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Channel @{username} already exists")

    ch = models.TelegramChannel(
        username=username,
        title=body.title or f"@{username}",
        is_active=body.is_active,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    await telegram_monitor.refresh_active_channels()
    logger.info("Channel added: @%s", username)
    return ch


@router.patch("/channels/{channel_id}", response_model=schemas.TelegramChannelResponse)
async def update_channel(
    channel_id: int,
    body: schemas.TelegramChannelUpdate,
    db: Session = Depends(get_db),
):
    ch = db.query(models.TelegramChannel).filter(models.TelegramChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ch, k, v)
    db.commit()
    db.refresh(ch)
    await telegram_monitor.refresh_active_channels()
    return ch


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    ch = db.query(models.TelegramChannel).filter(models.TelegramChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(ch)
    db.commit()
    await telegram_monitor.refresh_active_channels()
