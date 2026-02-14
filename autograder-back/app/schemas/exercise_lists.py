from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class ExerciseListCreate(BaseModel):
    """Schema for creating an exercise list"""
    title: str = Field(..., min_length=1, max_length=255)
    class_id: int
    group_id: Optional[int] = None
    opens_at: Optional[int] = None  # Unix timestamp
    closes_at: Optional[int] = None  # Unix timestamp
    late_penalty_percent_per_day: Optional[float] = Field(None, ge=0, le=100)
    auto_publish_grades: bool = True

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Title is required')
        return v.strip()

    @field_validator('closes_at')
    @classmethod
    def validate_dates(cls, v: Optional[int], info) -> Optional[int]:
        opens_at = info.data.get('opens_at')
        if v is not None and opens_at is not None and v <= opens_at:
            raise ValueError('closes_at must be after opens_at')
        return v


class ExerciseListResponse(BaseModel):
    """Schema for exercise list response"""
    id: int
    title: str
    class_id: int
    group_id: Optional[int]
    opens_at: Optional[int]
    closes_at: Optional[int]
    late_penalty_percent_per_day: Optional[float]
    auto_publish_grades: bool

    class Config:
        from_attributes = True


class ExerciseListDetailResponse(BaseModel):
    """Schema for detailed exercise list with items"""
    id: int
    title: str
    class_id: int
    group_id: Optional[int]
    opens_at: Optional[int]
    closes_at: Optional[int]
    late_penalty_percent_per_day: Optional[float]
    auto_publish_grades: bool
    exercises: List["ExerciseInList"]

    class Config:
        from_attributes = True


class ExerciseInList(BaseModel):
    """Schema for exercise within a list"""
    list_item_id: int
    exercise_id: int
    exercise_title: str
    position: int
    weight: float

    class Config:
        from_attributes = True


class AddExerciseToList(BaseModel):
    """Schema for adding exercise to list"""
    exercise_id: int
    position: int = Field(..., ge=1)
    weight: float = Field(1.0, gt=0)


class UpdateExercisePosition(BaseModel):
    """Schema for reordering exercise in list"""
    position: int = Field(..., ge=1)


class RemoveExerciseConfirmation(BaseModel):
    """Schema for confirming exercise removal"""
    confirm: bool = True
