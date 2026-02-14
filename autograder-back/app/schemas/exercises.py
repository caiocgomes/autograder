from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


class ProgrammingLanguage(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"


class ExerciseCreate(BaseModel):
    """Schema for creating an exercise"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    template_code: Optional[str] = None
    language: ProgrammingLanguage = ProgrammingLanguage.PYTHON

    # Constraints
    max_submissions: Optional[int] = Field(None, ge=1)
    timeout_seconds: int = Field(30, ge=1, le=300)
    memory_limit_mb: int = Field(512, ge=128, le=2048)

    # Grading configuration
    has_tests: bool = True
    llm_grading_enabled: bool = False
    test_weight: float = Field(0.7, ge=0.0, le=1.0)
    llm_weight: float = Field(0.3, ge=0.0, le=1.0)
    llm_grading_criteria: Optional[str] = None

    # Metadata
    published: bool = False
    tags: Optional[str] = None  # Comma-separated tags

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Title is required')
        return v.strip()

    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Description is required')
        return v.strip()

    def model_post_init(self, __context):
        """Validate grading configuration"""
        if not self.has_tests and not self.llm_grading_enabled:
            raise ValueError('At least one grading method required')

        if abs(self.test_weight + self.llm_weight - 1.0) > 0.01:
            raise ValueError('Test weight and LLM weight must sum to 1.0')


class ExerciseUpdate(BaseModel):
    """Schema for updating an exercise"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    template_code: Optional[str] = None

    # Constraints
    max_submissions: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    memory_limit_mb: Optional[int] = Field(None, ge=128, le=2048)

    # Grading configuration
    has_tests: Optional[bool] = None
    llm_grading_enabled: Optional[bool] = None
    test_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    llm_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    llm_grading_criteria: Optional[str] = None

    # Metadata
    published: Optional[bool] = None
    tags: Optional[str] = None


class ExerciseResponse(BaseModel):
    """Schema for exercise response"""
    id: int
    title: str
    description: str
    template_code: Optional[str]
    language: str

    # Constraints
    max_submissions: Optional[int]
    timeout_seconds: int
    memory_limit_mb: int

    # Grading configuration
    has_tests: bool
    llm_grading_enabled: bool
    test_weight: float
    llm_weight: float
    llm_grading_criteria: Optional[str]

    # Metadata
    created_by: int
    published: bool
    tags: Optional[str]

    # Relationships
    test_cases: Optional[List["TestCaseResponse"]] = None

    class Config:
        from_attributes = True


class TestCaseCreate(BaseModel):
    """Schema for creating a test case"""
    name: str = Field(..., min_length=1, max_length=255)
    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    hidden: bool = False

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Test name is required')
        return v.strip()


class TestCaseResponse(BaseModel):
    """Schema for test case response"""
    id: int
    exercise_id: int
    name: str
    input_data: str
    expected_output: str
    hidden: bool

    class Config:
        from_attributes = True


class DatasetUploadResponse(BaseModel):
    """Schema for dataset upload response"""
    filename: str
    file_url: str
    size_bytes: int
