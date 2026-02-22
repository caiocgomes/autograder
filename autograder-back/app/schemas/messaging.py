from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
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
    task_id: str
    total_recipients: int
    skipped_no_phone: int
    skipped_users: List[SkippedUser] = []
