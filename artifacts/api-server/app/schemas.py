from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime


class SourceBase(BaseModel):
    name: str
    type: str
    url: str
    is_active: bool = True


class SourceInput(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    events_count: int = 0


class EventInput(BaseModel):
    title: str
    title_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    category: str = "other"
    side: str = "neutral"
    confidence: float = 0.5
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    original_lang: str = "ar"
    raw_text: Optional[str] = None
    event_date: Optional[datetime] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    title_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    category: Optional[str] = None
    side: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_name: Optional[str] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    title_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    category: str
    side: str = "neutral"
    confidence: float
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    original_lang: str
    raw_text: Optional[str] = None
    event_hash: str
    is_duplicate: bool
    event_date: Optional[datetime] = None
    scraped_at: datetime
    created_at: datetime


class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
    offset: int
    limit: int


class CategoryCount(BaseModel):
    category: str
    count: int


class SourceCount(BaseModel):
    source_name: str
    count: int


class DailyCount(BaseModel):
    date: str
    count: int
    categories: Dict[str, int]


class DashboardStats(BaseModel):
    total_events: int
    events_today: int
    events_this_week: int
    by_category: List[CategoryCount]
    by_source: List[SourceCount]
    recent_timeline: List[DailyCount]


class ScraperStatus(BaseModel):
    is_running: bool
    last_run_at: Optional[datetime] = None
    last_run_events: int = 0
    last_run_errors: List[str] = []
    sources_count: int = 0


class HealthStatus(BaseModel):
    status: str
    version: str = "1.0.0"
    database: str = "connected"


# ── Telegram ──────────────────────────────────────────────────────────────────

class TelegramChannelInput(BaseModel):
    username: str
    title: Optional[str] = None
    is_active: bool = True


class TelegramChannelUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None


class ListenerStatus(BaseModel):
    """In-memory join/polling status for a Telegram channel (not persisted to DB)."""
    joined: bool = False
    error: Optional[str] = None
    polled_at: Optional[datetime] = None


class TelegramChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    title: Optional[str] = None
    channel_id: Optional[int] = None
    is_active: bool
    is_approved: bool
    approved_at: Optional[datetime] = None
    is_public_verified: bool
    last_message_id: int
    messages_processed: int
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    listener_status: Optional[ListenerStatus] = None   # injected by route, not from DB


class TelegramAuthStatus(BaseModel):
    configured: bool
    connected: bool
    authorized: bool
    phone: Optional[str] = None
    monitoring: bool
    channels_active: int
    messages_processed: int
    messages_rejected: int = 0
    raw_updates_received: int = 0
    last_message_at: Optional[datetime] = None
    error: Optional[str] = None


class TelegramCodeRequest(BaseModel):
    phone: str


class TelegramVerifyRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None
