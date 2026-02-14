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


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    classes_taught = relationship("Class", back_populates="professor", foreign_keys="Class.professor_id")
    enrollments = relationship("ClassEnrollment", back_populates="student")
    submissions = relationship("Submission", back_populates="student")
    group_memberships = relationship("GroupMembership", back_populates="student")
