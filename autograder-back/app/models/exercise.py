from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ProgrammingLanguage(str, enum.Enum):
    """Supported programming languages"""
    PYTHON = "python"


class Exercise(Base):
    """Exercise model with code problem and grading configuration"""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # Markdown with LaTeX support
    template_code = Column(Text, nullable=True)
    language = Column(Enum(ProgrammingLanguage), nullable=False, default=ProgrammingLanguage.PYTHON)

    # Constraints
    max_submissions = Column(Integer, nullable=True)  # null = unlimited
    timeout_seconds = Column(Integer, default=30, nullable=False)
    memory_limit_mb = Column(Integer, default=512, nullable=False)

    # Grading configuration
    has_tests = Column(Boolean, default=True, nullable=False)
    llm_grading_enabled = Column(Boolean, default=False, nullable=False)
    test_weight = Column(Float, default=0.7, nullable=False)  # Weight for test score
    llm_weight = Column(Float, default=0.3, nullable=False)  # Weight for LLM score
    llm_grading_criteria = Column(Text, nullable=True)  # Custom criteria for LLM

    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    published = Column(Boolean, default=False, nullable=False)
    tags = Column(String(500), nullable=True)  # Comma-separated tags

    # Relationships
    creator = relationship("User")
    test_cases = relationship("TestCase", back_populates="exercise")
    list_items = relationship("ExerciseListItem", back_populates="exercise")
    submissions = relationship("Submission", back_populates="exercise")


class TestCase(Base):
    """Test case for automated grading"""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    input_data = Column(Text, nullable=False)  # JSON or text input
    expected_output = Column(Text, nullable=False)
    hidden = Column(Boolean, default=False, nullable=False)  # Hide details from students

    # Relationships
    exercise = relationship("Exercise", back_populates="test_cases")


class ExerciseList(Base):
    """List of exercises assigned to a class"""
    __tablename__ = "exercise_lists"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)  # Optional group filter
    opens_at = Column(Integer, nullable=True)  # Unix timestamp
    closes_at = Column(Integer, nullable=True)  # Unix timestamp
    late_penalty_percent_per_day = Column(Float, nullable=True)
    auto_publish_grades = Column(Boolean, default=True, nullable=False)

    # Relationships
    class_ = relationship("Class", back_populates="exercise_lists")
    group = relationship("Group")
    items = relationship("ExerciseListItem", back_populates="list_")


class ExerciseListItem(Base):
    """Exercise within a list with ordering and weight"""
    __tablename__ = "exercise_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("exercise_lists.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # Order in list
    weight = Column(Float, default=1.0, nullable=False)  # Weight for final grade calculation

    # Relationships
    list_ = relationship("ExerciseList", back_populates="items")
    exercise = relationship("Exercise", back_populates="list_items")
