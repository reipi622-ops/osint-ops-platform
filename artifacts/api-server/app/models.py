from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # telegram, rss, web
    url = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="source", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    title_he = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    description_he = Column(Text, nullable=True)
    category = Column(String, default="other", index=True)
    confidence = Column(Float, default=0.5)

    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source_name = Column(String, nullable=True)
    source_url = Column(String, nullable=True)

    location_name = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    original_lang = Column(String, default="ar")
    raw_text = Column(Text, nullable=True)
    event_hash = Column(String, unique=True, index=True)
    is_duplicate = Column(Boolean, default=False)

    event_date = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="events")


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    channel_id = Column(Integer, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    last_message_id = Column(Integer, default=0)
    messages_processed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, nullable=True)
