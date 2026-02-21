"""
Snapshot de todos os compradores Hotmart, independente de onboarding na plataforma.

Uma linha por (email, hotmart_product_id).
user_id é NULL se o comprador ainda não criou conta na plataforma.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class HotmartBuyer(Base):
    __tablename__ = "hotmart_buyers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    hotmart_product_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)  # Ativo, Inadimplente, Cancelado, Reembolsado

    # NULL = sem conta na plataforma; SET NULL ao deletar o usuário
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("email", "hotmart_product_id", name="uq_hotmart_buyers_email_product"),
    )
