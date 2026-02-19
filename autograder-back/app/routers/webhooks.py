"""
Hotmart webhook receiver.

Receive-fast pattern: validate HMAC, persist raw event, return 200, enqueue Celery task.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event, EventStatus
from app.schemas.webhooks import WebhookResponse
from app.integrations.hotmart import validate_hottok, is_supported_event
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/hotmart", response_model=WebhookResponse)
async def hotmart_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receive Hotmart webhook events.
    Validates the hottok header, persists raw event, enqueues async processing.
    """
    # Validate signature
    hottok = request.headers.get("X-Hotmart-Hottok")
    if not validate_hottok(hottok, settings.hotmart_hottok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = payload.get("event", "unknown")

    # Determine status
    if not is_supported_event(event_type):
        event_status = EventStatus.IGNORED
    else:
        event_status = EventStatus.PROCESSED

    # Check idempotency by transaction_id
    transaction_id = payload.get("data", {}).get("purchase", {}).get("transaction")
    if transaction_id:
        existing = db.query(Event).filter(
            Event.type == f"hotmart.{event_type.lower()}",
            Event.payload["transaction_id"].astext == transaction_id,
        ).first()
        if existing:
            logger.info("Duplicate hotmart webhook: transaction_id=%s", transaction_id)
            return WebhookResponse(received=True, event_id=existing.id, message="Duplicate event, already processed")

    # Persist raw event
    event = Event(
        type=f"hotmart.{event_type.lower()}",
        payload={**payload, "transaction_id": transaction_id},
        status=event_status,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Enqueue async processing
    if event_status == EventStatus.PROCESSED and settings.hotmart_webhook_enabled:
        from app.tasks import process_hotmart_event
        process_hotmart_event.delay(event.id, payload)

    return WebhookResponse(received=True, event_id=event.id)
