import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class EventStatus(str, enum.Enum):
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class Event(Base):
    """Append-only event log for lifecycle actions, side-effects, and webhook processing"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(100), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.PROCESSED)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    actor = relationship("User", foreign_keys=[actor_id])
    target = relationship("User", foreign_keys=[target_id])
