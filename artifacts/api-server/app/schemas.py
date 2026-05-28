from pydantic import BaseModel, ConfigDict, computed_field, field_validator
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reliability_score(self) -> float:
        _type = getattr(self, "type", "") or ""
        if _type == "telegram":
            return 0.85
        if _type == "rss":
            return 0.60
        if _type == "web":
            return 0.55
        return 0.50


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
    is_important: bool = False
    importance_score: float = 0.0
    importance_tags: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v[:1000]  # hard cap

    @field_validator("raw_text", mode="before")
    @classmethod
    def cap_raw_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return str(v)[:5000]


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
    is_important: Optional[bool] = None


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
    is_important: bool = False
    importance_score: float = 0.0
    importance_tags: Optional[str] = None
    # Intelligence reliability fields
    confirmation_count: int = 0
    confirming_sources: Optional[str] = None
    has_media: bool = False
    propaganda_score: float = 0.0
    confidence_level: str = "low"
    escalation_level: str = "low"
    event_date: Optional[datetime] = None
    scraped_at: datetime
    created_at: datetime


class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
    offset: int
    limit: int


class HourlyCount(BaseModel):
    hour: str
    total: int
    red: int
    blue: int
    neutral: int


class EventTimelineResponse(BaseModel):
    hours: List[HourlyCount]
    window_hours: int


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


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    uptime_seconds: float
    sse_subscribers: int
    events_total: int
    events_today: int
    alerts_total: int


class HealthStatus(BaseModel):
    status: str
    version: str = "2.0.0"
    database: str = "connected"
    metrics: Optional[SystemMetrics] = None


# ── Telegram ──────────────────────────────────────────────────────────────────

# ── Intelligence patterns ──────────────────────────────────────────────────────

class PatternAlert(BaseModel):
    type: str
    severity: str
    description: str
    location_hint: Optional[str] = None
    event_ids: List[int] = []
    detected_at: str
    expires_at: str


class PatternListResponse(BaseModel):
    patterns: List[PatternAlert]
    total: int


# ── Geographic intelligence ────────────────────────────────────────────────────

class GeoCluster(BaseModel):
    grid_lat: float
    grid_lng: float
    center_lat: float
    center_lng: float
    radius_km: float
    event_count: int
    dominant_side: str
    last_event_at: Optional[str] = None
    threat_level: str
    event_ids: List[int] = []
    is_hotzone: bool


class GeoClusterListResponse(BaseModel):
    clusters: List[GeoCluster]
    total: int
    hotzones: int


# ── Source statistics ──────────────────────────────────────────────────────────

class ReliabilityPoint(BaseModel):
    date: str
    avg_confidence: float
    avg_propaganda: float
    event_count: int


class HourlyActivity(BaseModel):
    hour: int   # 0-23
    count: int


class PropagandaTrend(BaseModel):
    date: str
    avg_propaganda: float
    event_count: int


class SourceStats(BaseModel):
    source_id: int
    source_name: str
    source_type: str
    total_events: int
    avg_confidence: float
    avg_propaganda: float
    avg_importance: float
    important_events: int
    reliability_score: float
    reliability_history: List[ReliabilityPoint]  # last 14 days
    propaganda_trend: List[PropagandaTrend]       # last 14 days
    hourly_activity: List[HourlyActivity]         # activity by hour of day
    first_report_speed_seconds: Optional[float] = None  # avg seconds between event_date and scrape


class TelegramChannelInput(BaseModel):
    username: str
    title: Optional[str] = None
    is_active: bool = True


class TelegramChannelUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None


class ListenerStatus(BaseModel):
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
    listener_status: Optional[ListenerStatus] = None


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
