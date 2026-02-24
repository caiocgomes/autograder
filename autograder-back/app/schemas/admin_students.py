from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudentProductStatus(BaseModel):
    product_name: str
    status: str

    class Config:
        from_attributes = True


class StudentListItem(BaseModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    discord_connected: bool
    has_whatsapp: bool
    has_account: bool
    products: List[StudentProductStatus] = []

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    items: List[StudentListItem]
    total: int


class SyncTriggerRequest(BaseModel):
    product_id: Optional[int] = None


class SyncTriggerResponse(BaseModel):
    task_id: str


class SyncStatusTransitions(BaseModel):
    to_ativo: int = 0
    to_inadimplente: int = 0
    to_cancelado: int = 0
    to_reembolsado: int = 0


class SyncSummary(BaseModel):
    total_processed: int = 0
    new_students: int = 0
    status_changes: SyncStatusTransitions = SyncStatusTransitions()
    errors: int = 0


class SyncStatusResponse(BaseModel):
    status: str  # running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    summary: Optional[SyncSummary] = None
    error: Optional[str] = None
