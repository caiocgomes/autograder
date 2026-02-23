from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OnboardingStudentOut(BaseModel):
    id: int
    name: Optional[str] = None
    email: str
    whatsapp_number: Optional[str] = None
    lifecycle_status: Optional[str] = None
    token_status: str  # none, valid, expired, activated
    token_expires_in_days: Optional[int] = None
    last_message_at: Optional[datetime] = None


class OnboardingSummaryOut(BaseModel):
    total: int
    activated: int
    pending: int
    no_whatsapp: int
