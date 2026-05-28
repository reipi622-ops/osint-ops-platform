"""
Telegram channel monitor using Telethon.
Runs inside FastAPI's asyncio event loop — init_client() is awaited in lifespan.

Security policy (enforced in code):
  - WHITELIST ONLY: messages are processed only from manually added, admin-approved channels.
  - PUBLIC BROADCAST ONLY: only telethon.tl.types.Channel with broadcast=True and a public
    username are ever accepted. Private chats, groups, supergroups and user DMs are rejected
    at the handler level and logged.
  - NO CONTACT ACCESS: get_contacts() / get_dialogs() are never called.
  - NO PRIVATE DIALOGS: private message events are silently dropped.
  - AUDIT LOGGING: every accepted and every rejected message is logged with its source type.

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
_active_usernames: set[str] = set()  # only approved+active channels; refreshed on changes

# Captured once in init_client() — the uvicorn event loop — used in thread-safe broadcasts
_main_loop: Optional[asyncio.AbstractEventLoop] = None

# Per-channel join status: username → {"joined": bool, "error": str|None, "polled_at": datetime|None}
_channel_status: dict[str, dict] = {}

# Last processed message ID per channel (for dedup in polling fallback)
_channel_last_ids: dict[str, int] = {}

# Background polling task handle
_polling_task: Optional[asyncio.Task] = None

_status: dict = {
    "configured": False,
    "connected": False,
    "authorized": False,
    "phone": None,
    "monitoring": False,
    "channels_active": 0,
    "messages_processed": 0,
    "messages_rejected": 0,
    "raw_updates_received": 0,
    "last_message_at": None,
    "error": None,
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _normalize_username(raw: str) -> str:
    u = raw.strip()
    u = re.sub(r"^https?://t\.me/", "", u)
    u = re.sub(r"^t\.me/", "", u)
    u = u.lstrip("@")
    return u.lower()


def _is_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in text)


def _is_public_broadcast(chat) -> bool:
    try:
        from telethon.tl.types import Channel
    except ImportError:
        return False
    if not isinstance(chat, Channel):
        return False
    if not getattr(chat, "broadcast", False):
        return False
    if not getattr(chat, "username", None):
        return False
    return True


# ── public API ────────────────────────────────────────────────────────────────

def get_status() -> dict:
    return dict(_status)


def get_channel_status(username: str) -> dict:
    """Return the in-memory join/poll status for a given channel username."""
    norm = _normalize_username(username)
    return _channel_status.get(norm, {"joined": False, "error": "not_initialized", "polled_at": None})


async def init_client() -> None:
    """Called once from FastAPI lifespan. Safe to call even if not configured."""
    global _client, _main_loop

    _main_loop = asyncio.get_running_loop()

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

        # Exponential backoff reconnect (up to 5 attempts)
        connected = False
        for attempt in range(5):
            try:
                await _client.connect()
                connected = True
                _status["connected"] = True
                break
            except Exception as conn_exc:
                wait = 2 ** attempt
                logger.warning(
                    "Telegram: connect attempt %d/5 failed: %s — retrying in %ds",
                    attempt + 1, conn_exc, wait,
                )
                await asyncio.sleep(wait)

        if not connected:
            _status["error"] = "Failed to connect after 5 attempts"
            logger.error("Telegram: could not connect after 5 retries")
            return

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
    global _client, _polling_task
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
    if _client and _client.is_connected():
        await _client.disconnect()
    _status["connected"] = False
    _status["authorized"] = False
    _status["monitoring"] = False


async def request_code(phone: str) -> str:
    global _pending_phone_hash

    if not _client or not _client.is_connected():
        raise RuntimeError("Telegram client is not connected. Check API_ID / API_HASH.")

    result = await _client.send_code_request(phone)
    _pending_phone_hash = result.phone_code_hash
    _status["phone"] = phone
    logger.info("Telegram: code sent to %s", phone)
    return result.phone_code_hash


async def verify_code(phone: str, code: str, password: Optional[str] = None) -> None:
    global _pending_phone_hash

    if not _client:
        raise RuntimeError("Telegram client is not connected.")

    try:
        kwargs = {}
        if _pending_phone_hash:
            kwargs["phone_code_hash"] = _pending_phone_hash
        await _client.sign_in(phone=phone, code=code, **kwargs)
    except Exception as exc:
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


async def verify_public_channel(username: str) -> Optional[dict]:
    if not _client or not _client.is_connected():
        raise RuntimeError("Telegram client is not connected.")

    try:
        entity = await _client.get_entity(username)
    except Exception as exc:
        logger.warning("Telegram: could not resolve @%s: %s", username, exc)
        raise RuntimeError(f"Could not resolve @{username}: {exc}")

    if not _is_public_broadcast(entity):
        logger.warning(
            "Security: @%s rejected — not a public broadcast channel (type=%s broadcast=%s username=%s)",
            username,
            type(entity).__name__,
            getattr(entity, "broadcast", None),
            getattr(entity, "username", None),
        )
        return None

    return {
        "id": entity.id,
        "title": getattr(entity, "title", f"@{username}"),
    }


async def refresh_active_channels() -> None:
    """Reload approved+active channel usernames from DB, join new channels, restart polling."""
    global _active_usernames

    def _load():
        from app.database import SessionLocal
        from app import models
        db = SessionLocal()
        try:
            rows = (
                db.query(models.TelegramChannel)
                .filter(
                    models.TelegramChannel.is_active == True,
                    models.TelegramChannel.is_approved == True,
                )
                .all()
            )
            return {_normalize_username(r.username) for r in rows}, len(rows), [
                (_normalize_username(r.username), r.last_message_id) for r in rows
            ]
        finally:
            db.close()

    names, count, rows_info = await asyncio.to_thread(_load)

    new_channels = names - _active_usernames
    _active_usernames = names
    _status["channels_active"] = count

    for uname, last_id in rows_info:
        if uname not in _channel_last_ids and last_id:
            _channel_last_ids[uname] = last_id

    logger.info(
        "Security: whitelist refreshed — %d approved+active channel(s): %s",
        count, sorted(names),
    )

    if _client and _client.is_connected():
        for uname in names:
            await _join_channel(uname)


# ── channel joining ───────────────────────────────────────────────────────────

async def _join_channel(username: str) -> bool:
    global _client, _channel_status
    norm = _normalize_username(username)

    if not _client or not _client.is_connected():
        _channel_status[norm] = {"joined": False, "error": "client_not_connected", "polled_at": None}
        return False

    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        await _client(JoinChannelRequest(username))
        _channel_status[norm] = {"joined": True, "error": None, "polled_at": None}
        logger.info("Telegram: joined @%s — will now receive live messages", username)
        return True
    except Exception as exc:
        err = str(exc)[:120]
        _channel_status[norm] = {"joined": False, "error": err, "polled_at": None}
        logger.warning("Telegram: could not join @%s: %s", username, exc)
        return False


# ── polling fallback ──────────────────────────────────────────────────────────

async def _poll_channel_once(username: str, limit: int = 10) -> int:
    global _client, _channel_last_ids, _channel_status

    norm = _normalize_username(username)

    if not _client or not _client.is_connected():
        return 0

    try:
        entity = await _client.get_entity(username)
        last_id = _channel_last_ids.get(norm, 0)

        msgs = await _client.get_messages(entity, limit=limit, min_id=last_id)

        new_count = 0
        for msg in reversed(list(msgs)):
            if not msg.message:
                continue
            if msg.id <= last_id:
                continue
            _channel_last_ids[norm] = max(_channel_last_ids.get(norm, 0), msg.id)
            # Detect media evidence from the message object
            has_media = bool(getattr(msg, "media", None))
            await asyncio.to_thread(
                _process_message_sync, msg.message, username, entity.id, msg.id, has_media
            )
            new_count += 1

        now = datetime.utcnow()
        cs = _channel_status.get(norm, {"joined": False, "error": None})
        cs["polled_at"] = now
        _channel_status[norm] = cs

        if new_count:
            logger.info("Telegram: polled @%s — %d new message(s) fetched", username, new_count)
        return new_count

    except Exception as exc:
        logger.error("Telegram: poll error @%s: %s", username, exc)
        cs = _channel_status.get(norm, {"joined": False, "error": None, "polled_at": None})
        cs["error"] = str(exc)[:120]
        _channel_status[norm] = cs
        return 0


async def fetch_latest_messages(username: str, limit: int = 10) -> dict:
    norm = _normalize_username(username)
    _channel_last_ids.pop(norm, None)
    fetched = await _poll_channel_once(username, limit=limit)
    return {"fetched": fetched, "channel": username}


async def _poll_loop() -> None:
    logger.info("Telegram: polling fallback loop started (30 s interval)")
    while True:
        await asyncio.sleep(30)
        if not _active_usernames:
            continue
        for username in list(_active_usernames):
            try:
                await _poll_channel_once(username, limit=5)
            except Exception as exc:
                logger.error("Telegram: poll loop error @%s: %s", username, exc)


# ── monitoring ────────────────────────────────────────────────────────────────

async def _start_monitoring() -> None:
    global _handler_registered, _polling_task

    if not _client or not _client.is_connected():
        return

    if not _handler_registered:
        from telethon import events as tg_events

        @_client.on(tg_events.Raw)
        async def _raw_handler(update):
            _status["raw_updates_received"] += 1
            logger.debug("Telegram: raw update #%d — %s", _status["raw_updates_received"], type(update).__name__)

        _client.add_event_handler(_handle_message, tg_events.NewMessage)

        _handler_registered = True
        logger.info("Security: message handler registered (whitelist-only mode)")

    await refresh_active_channels()

    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
    _polling_task = asyncio.create_task(_poll_loop())

    _status["monitoring"] = True
    logger.info("Telegram: monitoring started (%d approved channels)", _status["channels_active"])


async def _handle_message(event) -> None:
    """
    Called by Telethon for every new message the account receives.

    Security gates (all must pass):
      1. Chat must be a public broadcast Channel (not a group, not a private chat, not a user DM)
      2. Chat must have a public username
      3. Username must be in the admin-approved whitelist
    """
    global _active_usernames

    chat_id_raw = getattr(event, "chat_id", "?")
    logger.info(
        "Telegram: NewMessage event received — chat_id=%s peer_id=%s",
        chat_id_raw,
        getattr(event, "peer_id", "?"),
    )

    try:
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None) or ""
        chat_id = getattr(chat, "id", None)
        chat_type = type(chat).__name__

        if not _is_public_broadcast(chat):
            _status["messages_rejected"] += 1
            logger.warning(
                "Security: dropped — not a public broadcast channel "
                "(type=%s, username=%s, broadcast=%s)",
                chat_type,
                chat_username or "<none>",
                getattr(chat, "broadcast", None),
            )
            return

        if not _active_usernames:
            _status["messages_rejected"] += 1
            logger.warning("Security: dropped — whitelist is empty (no approved channels)")
            return

        normalized = _normalize_username(chat_username)
        if normalized not in _active_usernames:
            _status["messages_rejected"] += 1
            logger.warning(
                "Security: dropped message from @%s — not in approved whitelist %s",
                chat_username, sorted(_active_usernames),
            )
            return

        text = event.message.message or ""
        if not text.strip():
            return

        msg_id = getattr(event.message, "id", 0)
        has_media = bool(getattr(event.message, "media", None))
        logger.info(
            "Security: ACCEPTED message from @%s msg_id=%s (%d chars) has_media=%s",
            chat_username, msg_id, len(text), has_media,
        )

        norm = _normalize_username(chat_username)
        _channel_last_ids[norm] = max(_channel_last_ids.get(norm, 0), msg_id)

        await asyncio.to_thread(
            _process_message_sync, text, chat_username, chat_id, msg_id, has_media
        )

    except Exception as exc:
        logger.error("Telegram message handler error: %s", exc)


def _process_message_sync(
    text: str,
    channel_username: str,
    channel_tg_id: Optional[int],
    message_id: int,
    has_media: bool = False,
) -> None:
    """Synchronous pipeline: translate → classify → importance → propaganda → geolocate → store → broadcast."""
    from app.database import SessionLocal
    from app import models
    from app.services.classifier import (
        classify_event,
        classify_side,
        detect_importance,
        detect_propaganda,
        detect_text_has_media_keywords,
        compute_confidence_level,
        compute_escalation_level,
    )
    from app.services.deduplicator import (
        compute_hash,
        is_near_duplicate,
        register_event,
        credit_confirmation,
    )
    from app.services.geolocator import extract_location
    from app.services.translator import translate_text
    from app.services.event_broadcaster import broadcaster

    db = SessionLocal()
    try:
        # ── Exact-dedup ──────────────────────────────────────────────────────
        event_hash = compute_hash(text, "")
        if db.query(models.Event).filter(models.Event.event_hash == event_hash).first():
            logger.debug("Telegram: skipping exact-duplicate msg_id=%s from @%s", message_id, channel_username)
            return

        # ── Near-dedup (multi-source confirmation) ───────────────────────────
        near_dup, near_dup_id = is_near_duplicate(text)
        if near_dup and near_dup_id:
            logger.info(
                "Telegram: near-duplicate msg_id=%s @%s → crediting event_id=%s as confirmation",
                message_id, channel_username, near_dup_id,
            )
            credit_confirmation(near_dup_id, f"@{channel_username}")
            # Register in dedup window so future identical messages are caught
            register_event(text, near_dup_id)
            # Feed pattern engine with this confirmation so coordinated detection can fire
            try:
                from app.services.pattern_engine import register_event_for_patterns
                register_event_for_patterns(
                    event_id=near_dup_id,
                    side="neutral",        # side unknown here; use neutral as placeholder
                    importance_score=0.5,  # placeholder — original score already in window
                    source_name=f"@{channel_username}",
                    event_hash=f"dup_{near_dup_id}",  # group key: all confirmations share this
                    location_hint=None,
                )
            except Exception as pe:
                logger.debug("Pattern engine near-dup registration skipped: %s", pe)
            return

        # ── Full classification pipeline ─────────────────────────────────────
        is_ar = _is_arabic(text)
        original_lang = "ar" if is_ar else "en"
        title_he = translate_text(text[:300], original_lang, "he") if is_ar else text[:300]
        desc_he = translate_text(text[300:1500], original_lang, "he") if (is_ar and len(text) > 300) else None

        category, confidence = classify_event(text, "")
        side, _side_conf = classify_side(text, "")
        is_important, importance_score, importance_tags = detect_importance(text, "")
        propaganda_score = detect_propaganda(text)

        # Media evidence: explicit attachment OR media keywords in text
        effective_has_media = has_media or detect_text_has_media_keywords(text)

        confidence_level = compute_confidence_level(
            confidence=confidence,
            importance_score=importance_score,
            confirmation_count=0,       # starts fresh; incremented by future near-dups
            has_media=effective_has_media,
            propaganda_score=propaganda_score,
        )

        escalation_level = compute_escalation_level(
            importance_score=importance_score,
            confidence=confidence,
            confirmation_count=0,
            confidence_level=confidence_level,
            threat_tags=importance_tags or "",
        )

        location_name, lat, lng = extract_location(text)

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
            side=side,
            confidence=confidence,
            is_important=is_important,
            importance_score=importance_score,
            importance_tags=importance_tags or None,
            has_media=effective_has_media,
            propaganda_score=propaganda_score,
            confidence_level=confidence_level,
            escalation_level=escalation_level,
            confirmation_count=0,
            confirming_sources=None,
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
        try:
            db.commit()
        except Exception as commit_exc:
            db.rollback()
            logger.debug(
                "Telegram: duplicate insert skipped (race condition) msg_id=%s @%s: %s",
                message_id, channel_username, commit_exc,
            )
            return
        db.refresh(ev)

        _status["messages_processed"] += 1
        _status["last_message_at"] = now

        register_event(text, ev.id)

        # Register in pattern engine (non-blocking; errors must not break the pipeline)
        try:
            from app.services.pattern_engine import register_event_for_patterns
            register_event_for_patterns(
                event_id=ev.id,
                side=side,
                importance_score=importance_score,
                source_name=f"@{channel_username}",
                event_hash=event_hash,
                location_hint=location_name,
            )
        except Exception as pe:
            logger.debug("Pattern engine registration skipped: %s", pe)

        if is_important:
            logger.info(
                "Telegram: ⚠ IMPORTANT event id=%d score=%.2f tags=[%s] level=%s escalation=%s @%s",
                ev.id, importance_score, importance_tags, confidence_level, escalation_level, channel_username,
            )
        if propaganda_score >= 0.50:
            logger.warning(
                "Telegram: ⚑ HIGH PROPAGANDA event id=%d score=%.2f @%s",
                ev.id, propaganda_score, channel_username,
            )

        from pydantic import TypeAdapter
        from app.schemas import EventResponse
        payload = TypeAdapter(EventResponse).validate_python(ev).model_dump(mode="json")

        if _main_loop and not _main_loop.is_closed():
            asyncio.run_coroutine_threadsafe(broadcaster.broadcast(payload), _main_loop)
        else:
            logger.warning("Telegram: _main_loop not available — SSE broadcast skipped")

        logger.info(
            "Telegram: stored event id=%d category=%s side=%s level=%s propaganda=%.2f @%s",
            ev.id, ev.category, ev.side, confidence_level, propaganda_score, channel_username,
        )

    except Exception as exc:
        db.rollback()
        logger.error("Telegram process_message error: %s", exc)
    finally:
        db.close()
