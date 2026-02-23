from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    openai_api_key_encrypted = Column(Text, nullable=True)
    anthropic_api_key_encrypted = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    updater = relationship("User", foreign_keys=[updated_by])
