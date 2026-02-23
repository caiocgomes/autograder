"""Schemas for system settings API."""
from typing import Optional
from pydantic import BaseModel


def mask_token(token: str) -> str:
    """Mask an API token: show first 10 chars + ****, or **** if too short."""
    if not token:
        return ""
    if len(token) < 10:
        return "****"
    return token[:10] + "****"


class SystemSettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class SystemSettingsResponse(BaseModel):
    openai_api_key_masked: str = ""
    anthropic_api_key_masked: str = ""
    openai_configured: bool = False
    anthropic_configured: bool = False
