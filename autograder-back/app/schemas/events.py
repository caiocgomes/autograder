from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict, List
from app.models.event import EventStatus


class EventResponse(BaseModel):
    id: int
    type: str
    actor_id: Optional[int] = None
    target_id: Optional[int] = None
    payload: Dict[str, Any] = {}
    status: EventStatus
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
