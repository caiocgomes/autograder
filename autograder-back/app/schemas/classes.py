from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class ClassCreate(BaseModel):
    """Schema for creating a new class"""
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Class name is required')
        return v.strip()


class ClassResponse(BaseModel):
    """Schema for class response"""
    id: int
    name: str
    professor_id: int
    invite_code: str
    archived: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClassDetailResponse(BaseModel):
    """Schema for detailed class response with roster"""
    id: int
    name: str
    professor_id: int
    invite_code: str
    archived: bool
    created_at: datetime
    students: list["StudentInClass"]
    groups: list["GroupResponse"]

    class Config:
        from_attributes = True


class StudentInClass(BaseModel):
    """Schema for student enrollment info"""
    id: int
    email: str
    enrolled_at: datetime

    class Config:
        from_attributes = True


class EnrollRequest(BaseModel):
    """Schema for student enrollment via invite code"""
    invite_code: str = Field(..., min_length=1)


class BulkEnrollRequest(BaseModel):
    """Schema for bulk CSV enrollment"""
    csv_data: str = Field(..., description="CSV content with 'email' and 'name' columns")


class BulkEnrollResponse(BaseModel):
    """Schema for bulk enrollment response"""
    created: int
    enrolled: int
    skipped: list[str]
    details: list[dict]


class GroupCreate(BaseModel):
    """Schema for creating a group"""
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Group name is required')
        return v.strip()


class GroupResponse(BaseModel):
    """Schema for group response"""
    id: int
    class_id: int
    name: str
    member_count: Optional[int] = None

    class Config:
        from_attributes = True


class GroupMemberAdd(BaseModel):
    """Schema for adding students to group"""
    student_ids: list[int] = Field(..., min_items=1)
