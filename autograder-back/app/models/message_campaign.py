import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class CampaignStatus(str, enum.Enum):
    SENDING = "sending"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class RecipientStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class MessageCampaign(Base):
    __tablename__ = "message_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    message_template = Column(Text, nullable=False)
    course_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    course_name = Column(String(255), nullable=True)
    sent_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CampaignStatus), nullable=False, default=CampaignStatus.SENDING)
    total_recipients = Column(Integer, nullable=False)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", foreign_keys=[sent_by])
    recipients = relationship("MessageRecipient", back_populates="campaign", cascade="all, delete-orphan")


class MessageRecipient(Base):
    __tablename__ = "message_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("message_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    name = Column(String(255), nullable=True)
    resolved_message = Column(Text, nullable=True)
    status = Column(Enum(RecipientStatus), nullable=False, default=RecipientStatus.PENDING)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    campaign = relationship("MessageCampaign", back_populates="recipients")
    user = relationship("User", foreign_keys=[user_id])
