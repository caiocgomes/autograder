from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


ALLOWED_VARIABLES = {"nome", "primeiro_nome", "email", "turma"}


class CourseOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class RecipientOut(BaseModel):
    id: int
    name: str
    email: str
    whatsapp_number: Optional[str] = None
    has_whatsapp: bool

    class Config:
        from_attributes = True


class SkippedUser(BaseModel):
    id: int
    name: str
    reason: str


class BulkSendRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1)
    message_template: str = Field(..., min_length=1)
    course_id: Optional[int] = None

    @field_validator("message_template")
    @classmethod
    def validate_template_variables(cls, v: str) -> str:
        found = set(re.findall(r"\{(\w+)\}", v))
        unknown = found - ALLOWED_VARIABLES
        if unknown:
            raise ValueError(f"Variáveis inválidas: {sorted(unknown)}. Permitidas: {sorted(ALLOWED_VARIABLES)}")
        return v


class BulkSendResponse(BaseModel):
    campaign_id: int
    task_id: str
    total_recipients: int
    skipped_no_phone: int
    skipped_users: List[SkippedUser] = []


class RecipientStatusOut(BaseModel):
    user_id: int
    name: Optional[str] = None
    phone: str
    status: str
    resolved_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignOut(BaseModel):
    id: int
    message_template: str
    course_name: Optional[str] = None
    total_recipients: int
    sent_count: int
    failed_count: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("message_template", mode="before")
    @classmethod
    def truncate_template(cls, v: str) -> str:
        if v and len(v) > 100:
            return v[:100] + "..."
        return v


class CampaignDetailOut(BaseModel):
    id: int
    message_template: str
    course_name: Optional[str] = None
    total_recipients: int
    sent_count: int
    failed_count: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    recipients: List[RecipientStatusOut] = []

    class Config:
        from_attributes = True


class RetryResponse(BaseModel):
    retrying: int
    campaign_id: int
