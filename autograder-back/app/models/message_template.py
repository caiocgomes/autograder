import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class TemplateEventType(str, enum.Enum):
    ONBOARDING = "onboarding"
    WELCOME = "welcome"
    WELCOME_BACK = "welcome_back"
    CHURN = "churn"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(Enum(TemplateEventType), unique=True, nullable=False)
    template_text = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    updater = relationship("User", foreign_keys=[updated_by])
