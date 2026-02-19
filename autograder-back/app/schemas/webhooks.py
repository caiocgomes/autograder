from pydantic import BaseModel
from typing import Optional, Any, Dict


class HotmartWebhookPayload(BaseModel):
    """Raw Hotmart webhook payload - flexible to accommodate all event types"""
    event: str
    data: Dict[str, Any] = {}

    class Config:
        extra = "allow"


class WebhookResponse(BaseModel):
    received: bool = True
    event_id: Optional[int] = None
    message: str = "OK"
