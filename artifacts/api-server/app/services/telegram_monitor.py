"""
Telegram channel monitor using Telethon.
Runs inside FastAPI's asyncio event loop — init_client() is awaited in lifespan.

Auth flow:
  1. POST /api/telegram/auth/request-code  → request_code(phone)
  2. POST /api/telegram/auth/verify-code   → verify_code(phone, code, [password])
  3. GET  /api/telegram/auth/status        → get_status()
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── module-level state ────────────────────────────────────────────────────────
_client = None          # TelegramClient instance (lazy import)
_pending_phone_hash: Optional[str] = None
_handler_registered = False
_active_usernames: set[str] = set()  # cached; refreshed on channel changes

_status: dict = {
    "configured": False,
    "connected": False,
    "authorized": False,
    "phone": None,
    "monitoring": False,
    "channels_active": 0,
    "messages_processed": 0,
    "last_message_at": None,
    "error": None,
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _normalize_username(raw: str) -> str:
    """Strip @, https://t.me/, t.me/ from channel identifiers."""
    u = raw.strip()
    u = re.sub(r"^https?://t\.me/", "", u)
    u = re.sub(r"^t\.me/", "", u)
    u = u.lstrip("@")
    return u.lower()


def _is_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in text)


# ── public API ────────────────────────────────────────────────────────────────

def get_status() -> dict:
    return dict(_status)


async def init_client() -> None:
    """Called once from FastAPI lifespan. Safe to call even if not configured."""
    global _client

    from app.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_PATH

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        _status["configured"] = False
        logger.info("Telegram: not configured (set TELEGRAM_API_ID + TELEGRAM_API_HASH)")
        return

    _status["configured"] = True

    try:
        from telethon import TelegramClient
        _client = TelegramClient(
            TELEGRAM_SESSION_PATH,
            int(TELEGRAM_API_ID),
            TELEGRAM_API_HASH,
        )
        await _client.connect()
        _status["connected"] = True

        if await _client.is_user_authorized():
            me = await _client.get_me()
            _status["authorized"] = True
            _status["phone"] = me.phone if me else None
            logger.info("Telegram: authorised as %s", _status["phone"])
            await _start_monitoring()
        else:
            logger.info("Telegram: connected — awaiting auth (/api/telegram/auth/request-code)")
    except Exception as exc:
        _status["error"] = str(exc)[:200]
        logger.error("Telegram init failed: %s", exc)


async def disconnect_client() -> None:
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
    _status["connected"] = False
    _status["authorized"] = False
    _status["monitoring"] = False


async def request_code(phone: str) -> str:
    """Sends a Telegram login code to the given phone. Returns phone_code_hash."""
    global _pending_phone_hash

    if not _client or not _client.is_connected():
        raise RuntimeError("Telegram client is not connected. Check API_ID / API_HASH.")

    result = await _client.send_code_request(phone)
    _pending_phone_hash = result.phone_code_hash
    _status["phone"] = phone
    logger.info("Telegram: code sent to %s", phone)
    return result.phone_code_hash


async def verify_code(phone: str, code: str, password: Optional[str] = None) -> None:
    """Completes sign-in with the received code (and optional 2FA password)."""
    global _pending_phone_hash

    if not _client:
        raise RuntimeError("Telegram client is not connected.")

    try:
        from telethon.errors import SessionPasswordNeededError
        kwargs = {}
        if _pending_phone_hash:
            kwargs["phone_code_hash"] = _pending_phone_hash

        await _client.sign_in(phone=phone, code=code, **kwargs)

    except Exception as exc:
        # Check for 2FA requirement without importing the class
        if "SessionPasswordNeededError" in type(exc).__name__ or "password" in str(exc).lower():
            if not password:
                raise ValueError("Two-factor authentication is enabled. Provide your 2FA password.")
            await _client.sign_in(password=password)
        else:
            raise

    _pending_phone_hash = None
    me = await _client.get_me()
    _status["authorized"] = True
    _status["phone"] = me.phone if me else phone
    _status["error"] = None
    logger.info("Telegram: auth complete for %s", _status["phone"])
    await _start_monitoring()


async def logout() -> None:
    global _pending_phone_hash
    if _client and _client.is_connected():
        try:
            await _client.log_out()
        except Exception:
            pass
    _status["authorized"] = False
    _status["phone"] = None
    _status["monitoring"] = False
    _pending_phone_hash = None
    logger.info("Telegram: logged out")


async def refresh_active_channels() -> None:
    """Reload monitored usernames from DB into the in-memory cache."""
    global _active_usernames

    def _load():
        from app.database import SessionLocal
        from app import models
        db = SessionLocal()
        try:
            rows = (
                db.query(models.TelegramChannel)
                .filter(models.TelegramChannel.is_active == True)
                .all()
            )
            return {_normalize_username(r.username) for r in rows}, len(rows)
        finally:
            db.close()

    names, count = await asyncio.to_thread(_load)
    _active_usernames = names
    _status["channels_active"] = count
    logger.debug("Telegram: active channels refreshed (%d)", count)


# ── monitoring ────────────────────────────────────────────────────────────────

async def _start_monitoring() -> None:
    global _handler_registered

    if not _client or not _client.is_connected():
        return

    if not _handler_registered:
        from telethon import events as tg_events
        _client.add_event_handler(_handle_message, tg_events.NewMessage)
        _handler_registered = True

    await refresh_active_channels()
    _status["monitoring"] = True
    logger.info("Telegram: monitoring started (%d channels)", _status["channels_active"])


async def _handle_message(event) -> None:
    """Called by Telethon for every new message received by the account."""
    global _active_usernames

    try:
        # Determine the chat's username so we can match it
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None) or ""
        chat_id = getattr(chat, "id", None)

        # Must be from a monitored channel
        if not _active_usernames:
            return

        is_monitored = (
            _normalize_username(chat_username) in _active_usernames
            if chat_username
            else False
        )
        if not is_monitored:
            return

        text = event.message.message or ""
        if not text.strip():
            return

        logger.info("Telegram: new message from @%s (%d chars)", chat_username, len(text))
        await asyncio.to_thread(_process_message_sync, text, chat_username, chat_id, event.message.id)

    except Exception as exc:
        logger.error("Telegram message handler error: %s", exc)


def _process_message_sync(
    text: str,
    channel_username: str,
    channel_tg_id: Optional[int],
    message_id: int,
) -> None:
    """Synchronous pipeline: translate → classify → geolocate → store → broadcast."""
    from app.database import SessionLocal
    from app import models
    from app.services.classifier import classify_event
    from app.services.deduplicator import compute_hash
    from app.services.geolocator import extract_location
    from app.services.translator import translate_text
    from app.services.event_broadcaster import broadcaster
    import asyncio

    db = SessionLocal()
    try:
        # Deduplication
        event_hash = compute_hash(text, "")
        if db.query(models.Event).filter(models.Event.event_hash == event_hash).first():
            return

        # Language detection + translation
        is_ar = _is_arabic(text)
        original_lang = "ar" if is_ar else "en"
        title_he = translate_text(text[:300], original_lang, "he") if is_ar else text[:300]
        desc_he = translate_text(text[300:1500], original_lang, "he") if (is_ar and len(text) > 300) else None

        # Classification + geolocation
        category, confidence = classify_event(text, "")
        location_name, lat, lng = extract_location(text)

        # Find or create a Source record for this channel
        source_url = f"https://t.me/{channel_username}"
        source = db.query(models.Source).filter(models.Source.url == source_url).first()
        if not source:
            source = models.Source(
                name=f"Telegram: @{channel_username}",
                type="telegram",
                url=source_url,
                is_active=True,
            )
            db.add(source)
            db.flush()

        now = datetime.utcnow()
        ev = models.Event(
            title=text[:500],
            title_he=title_he,
            description=text[:2000] if len(text) > 300 else None,
            description_he=desc_he,
            category=category,
            confidence=confidence,
            source_id=source.id,
            source_name=source.name,
            source_url=source_url,
            location_name=location_name,
            lat=lat,
            lng=lng,
            original_lang=original_lang,
            raw_text=text[:2000],
            event_hash=event_hash,
            is_duplicate=False,
            event_date=now,
            scraped_at=now,
            created_at=now,
        )
        db.add(ev)

        # Update channel stats
        ch = (
            db.query(models.TelegramChannel)
            .filter(models.TelegramChannel.username.ilike(channel_username))
            .first()
        )
        if ch:
            ch.messages_processed = (ch.messages_processed or 0) + 1
            ch.last_activity_at = now
            if channel_tg_id:
                ch.channel_id = channel_tg_id
            ch.last_message_id = message_id

        source.last_scraped_at = now
        db.commit()
        db.refresh(ev)

        # Update in-memory stats
        _status["messages_processed"] += 1
        _status["last_message_at"] = now

        # Broadcast to SSE clients (schedule coroutine from sync thread)
        from pydantic import TypeAdapter
        from app.schemas import EventResponse
        payload = TypeAdapter(EventResponse).validate_python(ev).model_dump(mode="json")
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(broadcaster.broadcast(payload), loop)

        logger.info(
            "Telegram: stored event id=%d category=%s from @%s",
            ev.id, ev.category, channel_username,
        )

    except Exception as exc:
        db.rollback()
        logger.error("Telegram process_message error: %s", exc)
    finally:
        db.close()
