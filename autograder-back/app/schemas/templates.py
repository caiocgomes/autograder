import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# Valid template variables per event type
TEMPLATE_VARIABLES = {
    "onboarding": {"primeiro_nome", "nome", "token", "product_name"},
    "welcome": {"primeiro_nome", "nome", "product_name"},
    "welcome_back": {"primeiro_nome", "nome", "product_name"},
    "churn": {"primeiro_nome", "nome", "product_name"},
}

ALL_TEMPLATE_VARIABLES = set()
for v in TEMPLATE_VARIABLES.values():
    ALL_TEMPLATE_VARIABLES |= v


class TemplateOut(BaseModel):
    event_type: str
    template_text: str
    is_default: bool = False
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateUpdateRequest(BaseModel):
    template_text: str = Field(..., min_length=1)
