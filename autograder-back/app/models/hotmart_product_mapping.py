"""
Relação de/para configurável entre produto comprado na Hotmart e produtos internos concedidos.

Uma linha por (source_hotmart_product_id, target_product_id).
Permite que um produto Hotmart (ex: "A Base de Tudo") conceda acesso a múltiplos produtos internos.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class HotmartProductMapping(Base):
    __tablename__ = "hotmart_product_mapping"

    id = Column(Integer, primary_key=True, index=True)

    # ID do produto comprado na Hotmart (string raw, não FK — pode não estar configurado como Product interno)
    source_hotmart_product_id = Column(String(255), nullable=False, index=True)

    # Produto interno concedido. CASCADE: se o produto interno for deletado, remove o mapping.
    target_product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    target_product = relationship("Product", foreign_keys=[target_product_id])

    __table_args__ = (
        UniqueConstraint(
            "source_hotmart_product_id",
            "target_product_id",
            name="uq_hotmart_product_mapping_source_target",
        ),
    )
