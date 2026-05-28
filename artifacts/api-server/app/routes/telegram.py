"""
Telegram admin routes:
  Auth:     GET/POST /telegram/auth/status|request-code|verify-code|logout
  Channels: GET/POST/PATCH/DELETE /telegram/channels[/{id}]
            POST /telegram/channels/{id}/approve
"""
import logging
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services import telegram_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

_USERNAME_RE = re.compile(r"^https?://t\.me/", re.I)


def _clean_username(raw: str) -> str:
    return _USERNAME_RE.sub("", raw.strip()).lstrip("@").lower()


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
        messages_rejected=s.get("messages_rejected", 0),
        raw_updates_received=s.get("raw_updates_received", 0),
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
    rows = (
        db.query(models.TelegramChannel)
        .order_by(models.TelegramChannel.created_at.desc())
        .all()
    )
    results = []
    for ch in rows:
        r = schemas.TelegramChannelResponse.model_validate(ch)
        raw_ls = telegram_monitor.get_channel_status(ch.username)
        r.listener_status = schemas.ListenerStatus(**{
            "joined": raw_ls.get("joined", False),
            "error": raw_ls.get("error"),
            "polled_at": raw_ls.get("polled_at"),
        })
        results.append(r)
    return results


@router.post("/channels", response_model=schemas.TelegramChannelResponse, status_code=201)
async def add_channel(body: schemas.TelegramChannelInput, db: Session = Depends(get_db)):
    username = _clean_username(body.username)
    if not username:
        raise HTTPException(status_code=422, detail="Invalid channel username")

    existing = db.query(models.TelegramChannel).filter(
        models.TelegramChannel.username.ilike(username)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Channel @{username} already exists")

    # Verify this is a real, public broadcast channel via Telethon
    is_public_verified = False
    resolved_title = body.title or f"@{username}"
    channel_tg_id = None

    status = telegram_monitor.get_status()
    if status["authorized"]:
        try:
            entity_info = await telegram_monitor.verify_public_channel(username)
            if entity_info is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"@{username} is not a public broadcast channel. "
                        "Only public Telegram channels (not groups, not private chats) "
                        "may be added."
                    ),
                )
            is_public_verified = True
            resolved_title = entity_info.get("title") or resolved_title
            channel_tg_id = entity_info.get("id")
            logger.info(
                "Security: verified @%s is a public broadcast channel (id=%s)",
                username, channel_tg_id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Could not verify @{username}: {exc}"
            )
    else:
        logger.warning(
            "Security: adding @%s without verification (Telegram not authorized)", username
        )

    ch = models.TelegramChannel(
        username=username,
        title=resolved_title,
        channel_id=channel_tg_id,
        is_active=False,        # must be explicitly activated after approval
        is_approved=False,      # requires manual approval before monitoring starts
        is_public_verified=is_public_verified,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    logger.info(
        "Security audit: channel @%s added — pending approval (verified_public=%s)",
        username, is_public_verified,
    )
    return ch


@router.post("/channels/{channel_id}/approve", response_model=schemas.TelegramChannelResponse)
async def approve_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    Explicitly approve a channel for monitoring.
    Only approved + active channels receive messages.
    This action is logged for audit purposes.
    """
    ch = db.query(models.TelegramChannel).filter(
        models.TelegramChannel.id == channel_id
    ).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not ch.is_public_verified:
        status = telegram_monitor.get_status()
        if status["authorized"]:
            try:
                entity_info = await telegram_monitor.verify_public_channel(ch.username)
                if entity_info is None:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"@{ch.username} failed public-channel verification. "
                            "Cannot approve a non-public or non-broadcast source."
                        ),
                    )
                ch.is_public_verified = True
                if entity_info.get("id"):
                    ch.channel_id = entity_info["id"]
                if entity_info.get("title"):
                    ch.title = entity_info["title"]
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=422, detail=f"Verification failed: {exc}")

    ch.is_approved = True
    ch.approved_at = datetime.utcnow()
    ch.is_active = True
    db.commit()
    db.refresh(ch)

    # refresh_active_channels() also joins the channel so Telethon receives live events
    await telegram_monitor.refresh_active_channels()
    # Immediately backfill the last 10 messages after joining
    try:
        await telegram_monitor.fetch_latest_messages(ch.username, limit=10)
    except Exception as exc:
        logger.warning("Could not backfill @%s after approval: %s", ch.username, exc)

    logger.info(
        "Security audit: channel @%s APPROVED for monitoring at %s",
        ch.username, ch.approved_at.isoformat(),
    )
    r = schemas.TelegramChannelResponse.model_validate(ch)
    raw_ls = telegram_monitor.get_channel_status(ch.username)
    r.listener_status = schemas.ListenerStatus(**{
        "joined": raw_ls.get("joined", False),
        "error": raw_ls.get("error"),
        "polled_at": raw_ls.get("polled_at"),
    })
    return r


@router.patch("/channels/{channel_id}", response_model=schemas.TelegramChannelResponse)
async def update_channel(
    channel_id: int,
    body: schemas.TelegramChannelUpdate,
    db: Session = Depends(get_db),
):
    ch = db.query(models.TelegramChannel).filter(
        models.TelegramChannel.id == channel_id
    ).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = body.model_dump(exclude_none=True)

    # Prevent activating an unapproved channel via PATCH
    if updates.get("is_active") is True and not ch.is_approved:
        raise HTTPException(
            status_code=422,
            detail="Channel must be approved before it can be activated. Use POST /approve first.",
        )

    for k, v in updates.items():
        setattr(ch, k, v)

    db.commit()
    db.refresh(ch)
    await telegram_monitor.refresh_active_channels()
    logger.info("Security audit: channel @%s updated: %s", ch.username, list(updates.keys()))
    return ch


@router.post("/channels/{channel_id}/test-fetch")
async def test_fetch_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    Manually fetch the latest 10 messages from a channel and process any new ones.
    Useful for testing whether the listener is working.
    """
    ch = db.query(models.TelegramChannel).filter(models.TelegramChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not telegram_monitor.get_status()["authorized"]:
        raise HTTPException(status_code=503, detail="Telegram is not authorized")
    try:
        result = await telegram_monitor.fetch_latest_messages(ch.username, limit=10)
        logger.info("Manual test fetch: @%s — %d messages fetched", ch.username, result["fetched"])
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    ch = db.query(models.TelegramChannel).filter(
        models.TelegramChannel.id == channel_id
    ).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    logger.info(
        "Security audit: channel @%s REMOVED from monitoring whitelist", ch.username
    )
    db.delete(ch)
    db.commit()
    await telegram_monitor.refresh_active_channels()
