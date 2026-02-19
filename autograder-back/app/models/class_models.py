import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class EnrollmentSource(str, enum.Enum):
    MANUAL = "manual"
    PRODUCT = "product"


class Class(Base):
    """Class model for organizing students and exercises"""
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invite_code = Column(String(16), unique=True, nullable=False, index=True)
    archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    professor = relationship("User", back_populates="classes_taught", foreign_keys=[professor_id])
    enrollments = relationship("ClassEnrollment", back_populates="class_")
    groups = relationship("Group", back_populates="class_")
    exercise_lists = relationship("ExerciseList", back_populates="class_")


class ClassEnrollment(Base):
    """Enrollment relationship between students and classes"""
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint('class_id', 'student_id', name='uq_class_student'),
        Index('ix_class_enrollments_class_student', 'class_id', 'student_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    enrollment_source = Column(Enum(EnrollmentSource), nullable=False, default=EnrollmentSource.MANUAL)

    # Relationships
    class_ = relationship("Class", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments")


class Group(Base):
    """Group within a class for targeted exercise assignments"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Relationships
    class_ = relationship("Class", back_populates="groups")
    memberships = relationship("GroupMembership", back_populates="group")


class GroupMembership(Base):
    """Membership relationship between students and groups"""
    __tablename__ = "group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    group = relationship("Group", back_populates="memberships")
    student = relationship("User", back_populates="group_memberships")
