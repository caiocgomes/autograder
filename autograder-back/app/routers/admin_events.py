"""
Admin event log viewer, manual retry, and manual sync triggers.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event, EventStatus
from app.models.user import UserRole
from app.schemas.events import EventResponse, EventListResponse
from app.auth.dependencies import require_role, get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/events", tags=["Admin Events"])

admin_only = require_role(UserRole.ADMIN)


@router.get("", response_model=EventListResponse)
def list_events(
    status: Optional[str] = Query(None, description="Filter by status: processed, failed, ignored"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    target_id: Optional[int] = Query(None, description="Filter by target student ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    """List events with optional filters. Default returns all events ordered by most recent."""
    query = db.query(Event)

    if status:
        try:
            status_enum = EventStatus(status)
            query = query.filter(Event.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if event_type:
        query = query.filter(Event.type == event_type)

    if target_id:
        query = query.filter(Event.target_id == target_id)

    total = query.count()
    items = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()

    return EventListResponse(items=items, total=total)


@router.post("/{event_id}/retry", response_model=EventResponse)
def retry_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(admin_only),
):
    """
    Manually retry a failed event.
    Creates an admin.manual_retry event and re-enqueues the side-effect.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != EventStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed events can be retried")

    # Log the retry action
    retry_event_log = Event(
        type="admin.manual_retry",
        actor_id=current_user.id,
        target_id=event.target_id,
        payload={"original_event_id": event.id, "original_type": event.type},
        status=EventStatus.PROCESSED,
    )
    db.add(retry_event_log)

    # Enqueue the side-effect retry
    from app.tasks import execute_side_effect
    execute_side_effect.delay(event.id)

    db.commit()
    db.refresh(event)
    return event


class HotmartSyncRequest(BaseModel):
    product_id: Optional[int] = None


@router.post("/hotmart-sync")
def trigger_hotmart_sync(
    body: HotmartSyncRequest = HotmartSyncRequest(),
    _: None = Depends(admin_only),
):
    """
    Manually trigger a Hotmart buyer reconciliation sync.
    Enqueues sync_hotmart_students as a Celery task.
    """
    from app.tasks import sync_hotmart_students
    task = sync_hotmart_students.delay(body.product_id)
    return {"task_id": task.id, "message": "Sync enqueued"}


@router.post("/course-status-sync")
def trigger_course_status_sync(
    body: HotmartSyncRequest = HotmartSyncRequest(),
    _: None = Depends(admin_only),
):
    """
    Manually trigger student course status sync for all products (or a specific one).
    Updates student_course_status SCD2 table from Hotmart data.
    """
    from app.tasks import sync_student_course_status
    task = sync_student_course_status.delay(body.product_id)
    return {"task_id": task.id, "message": "Course status sync enqueued"}
