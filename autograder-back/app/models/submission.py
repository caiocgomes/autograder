from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Float, DateTime, Enum, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class SubmissionStatus(str, enum.Enum):
    """Submission processing status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Submission(Base):
    """Student code submission"""
    __tablename__ = "submissions"
    __table_args__ = (
        Index('ix_submissions_exercise_student_submitted', 'exercise_id', 'student_id', 'submitted_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(Text, nullable=False)
    code_hash = Column(String(64), nullable=False, index=True)  # SHA256 for LLM cache
    status = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.QUEUED)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    exercise = relationship("Exercise", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    test_results = relationship("TestResult", back_populates="submission")
    llm_evaluation = relationship("LLMEvaluation", back_populates="submission", uselist=False)
    grade = relationship("Grade", back_populates="submission", uselist=False)


class TestResult(Base):
    """Result from a single test case execution"""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    passed = Column(Boolean, nullable=False)
    message = Column(Text, nullable=True)  # Error message or details
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="test_results")


class LLMEvaluation(Base):
    """LLM-generated qualitative feedback and score"""
    __tablename__ = "llm_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, unique=True, index=True)
    code_hash = Column(String(64), nullable=False, index=True)  # For cache lookups
    feedback = Column(Text, nullable=False)
    score = Column(Float, nullable=False)  # 0-100
    cached = Column(Boolean, default=False, nullable=False)  # Was this from cache?
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("Submission", back_populates="llm_evaluation")


class Grade(Base):
    """Final grade for a submission"""
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, unique=True, index=True)
    test_score = Column(Float, nullable=True)  # 0-100 or null if no tests
    llm_score = Column(Float, nullable=True)  # 0-100 or null if no LLM
    final_score = Column(Float, nullable=False)  # Composite score 0-100
    late_penalty_applied = Column(Float, default=0.0, nullable=False)  # Percentage deducted
    published = Column(Boolean, default=False, nullable=False)  # Visible to student?

    # Relationships
    submission = relationship("Submission", back_populates="grade")
