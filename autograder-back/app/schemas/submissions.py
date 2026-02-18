from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubmissionStatus(str, Enum):
    """Submission processing status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmissionCreate(BaseModel):
    """Schema for creating a submission via text input"""
    exercise_id: int = Field(..., gt=0)
    code: Optional[str] = Field(None, min_length=1)


class SubmissionResponse(BaseModel):
    """Schema for submission response"""
    id: int
    exercise_id: int
    student_id: int
    code: Optional[str] = None
    status: SubmissionStatus
    submitted_at: datetime
    error_message: Optional[str] = None

    # File upload fields
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """Schema for listing submissions"""
    id: int
    exercise_id: int
    student_id: int
    status: SubmissionStatus
    submitted_at: datetime
    file_name: Optional[str] = None

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    """Schema for test result response"""
    id: int
    test_name: str
    passed: bool
    message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    class Config:
        from_attributes = True


class LLMEvaluationResponse(BaseModel):
    """Schema for LLM evaluation response"""
    id: int
    feedback: str
    score: float
    cached: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GradeResponse(BaseModel):
    """Schema for grade response"""
    id: int
    test_score: Optional[float] = None
    llm_score: Optional[float] = None
    final_score: float
    late_penalty_applied: float
    published: bool

    class Config:
        from_attributes = True


class RubricScoreResponse(BaseModel):
    """Schema for rubric score response"""
    dimension_name: str
    dimension_weight: float
    score: float
    feedback: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionDetailResponse(BaseModel):
    """Schema for detailed submission response with results"""
    submission: SubmissionResponse
    test_results: Optional[List[TestResultResponse]] = None
    llm_evaluation: Optional[LLMEvaluationResponse] = None
    grade: Optional[GradeResponse] = None
    rubric_scores: Optional[List[RubricScoreResponse]] = None
    overall_feedback: Optional[str] = None
