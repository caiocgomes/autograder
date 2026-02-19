import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class AccessRuleType(str, enum.Enum):
    DISCORD_ROLE = "discord_role"
    CLASS_ENROLLMENT = "class_enrollment"
    MANYCHAT_TAG = "manychat_tag"


class Product(Base):
    """Maps Hotmart products to access rules (Discord roles, classes, ManyChat tags)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    hotmart_product_id = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    access_rules = relationship("ProductAccessRule", back_populates="product", cascade="all, delete-orphan")


class ProductAccessRule(Base):
    """Defines what access a product grants (Discord role, class, or ManyChat tag)"""
    __tablename__ = "product_access_rules"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    rule_type = Column(Enum(AccessRuleType), nullable=False)
    rule_value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="access_rules")
