from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    PROFESSOR = "professor"
    STUDENT = "student"
    TA = "ta"


class LifecycleStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PENDING_ONBOARDING = "pending_onboarding"
    ACTIVE = "active"
    CHURNED = "churned"


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Integration fields for lifecycle management
    hotmart_id = Column(String(255), unique=True, nullable=True, index=True)
    discord_id = Column(String(255), unique=True, nullable=True, index=True)
    whatsapp_number = Column(String(20), nullable=True)
    lifecycle_status = Column(Enum(LifecycleStatus), nullable=True)
    onboarding_token = Column(String(16), unique=True, nullable=True, index=True)
    onboarding_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    manychat_subscriber_id = Column(String(255), nullable=True)

    # Relationships
    classes_taught = relationship("Class", back_populates="professor", foreign_keys="Class.professor_id")
    enrollments = relationship("ClassEnrollment", back_populates="student")
    submissions = relationship("Submission", back_populates="student")
    group_memberships = relationship("GroupMembership", back_populates="student")
