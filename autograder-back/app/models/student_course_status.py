"""
SCD Type 2 table for student course status history.

One row per status version per (user_id, product_id).
Current state: is_current = True (valid_to = NULL).
History: is_current = False (valid_to set to when status changed).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class StudentCourseStatus(Base):
    __tablename__ = "student_course_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # Business status: Ativo, Inadimplente, Cancelado, Reembolsado
    status = Column(String(50), nullable=False)

    # SCD Type 2 validity range
    valid_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_to = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)

    # Audit
    source = Column(String(50), nullable=True)  # e.g. "hotmart_sync", "webhook"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    product = relationship("Product")

    __table_args__ = (
        # Partial unique index: only one current row per (user, product)
        # Enforced at application level; DB index below is advisory
        Index("ix_student_course_status_current", "user_id", "product_id",
              postgresql_where=Column("is_current") == True),
    )
