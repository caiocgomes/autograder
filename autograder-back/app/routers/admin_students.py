"""
Admin student listing and Hotmart sync trigger endpoints.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer
from app.schemas.admin_students import (
    StudentListItem,
    StudentListResponse,
    StudentProductStatus,
    SyncTriggerRequest,
    SyncTriggerResponse,
    SyncStatusResponse,
)
from app.auth.dependencies import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/students", tags=["Admin Students"])

admin_only = require_role(UserRole.ADMIN)


@router.get("", response_model=StudentListResponse)
def list_students(
    status: Optional[str] = Query(None, description="Filter by status: Ativo, Inadimplente, Cancelado, Reembolsado"),
    discord: Optional[str] = Query(None, description="Filter by Discord: true or false"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    """List all Hotmart buyers with aggregated product statuses."""

    # Build product lookup
    products = {str(p.hotmart_product_id): p.name for p in db.query(Product).all()}

    # Get distinct emails from hotmart_buyers with filters
    buyer_query = db.query(HotmartBuyer)

    if status:
        buyer_query = buyer_query.filter(HotmartBuyer.status == status)

    if product_id:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            buyer_query = buyer_query.filter(
                HotmartBuyer.hotmart_product_id == str(product.hotmart_product_id)
            )

    if search:
        buyer_query = buyer_query.filter(
            (HotmartBuyer.email.ilike(f"%{search}%")) |
            (HotmartBuyer.name.ilike(f"%{search}%"))
        )

    # Get distinct emails matching filters
    filtered_emails_query = buyer_query.with_entities(HotmartBuyer.email).distinct()

    # Discord filter needs User join
    if discord:
        user_emails_with_discord = (
            db.query(User.email)
            .filter(User.discord_id.isnot(None))
            .subquery()
        )
        if discord == "true":
            filtered_emails_query = filtered_emails_query.filter(
                HotmartBuyer.email.in_(user_emails_with_discord)
            )
        elif discord == "false":
            filtered_emails_query = filtered_emails_query.filter(
                ~HotmartBuyer.email.in_(user_emails_with_discord)
            )

    # Count total distinct emails
    total = filtered_emails_query.count()

    # Paginate emails
    email_rows = (
        filtered_emails_query
        .order_by(HotmartBuyer.email)
        .offset(offset)
        .limit(limit)
        .all()
    )
    page_emails = [row[0] for row in email_rows]

    if not page_emails:
        return StudentListResponse(items=[], total=total)

    # Batch-load all buyer records for this page of emails
    all_buyers = (
        db.query(HotmartBuyer)
        .filter(HotmartBuyer.email.in_(page_emails))
        .all()
    )

    # Group by email
    buyers_by_email = {}
    for b in all_buyers:
        buyers_by_email.setdefault(b.email, []).append(b)

    # Load users for these emails
    users = db.query(User).filter(User.email.in_(page_emails)).all()
    user_by_email = {u.email: u for u in users}

    # Assemble response
    items = []
    for email in page_emails:
        buyer_records = buyers_by_email.get(email, [])
        user = user_by_email.get(email)

        # Pick name/phone from first buyer record that has them
        name = None
        phone = None
        for b in buyer_records:
            if not name and b.name:
                name = b.name
            if not phone and b.phone:
                phone = b.phone

        # If user exists, prefer user's name
        if user and user.full_name:
            name = user.full_name

        product_statuses = []
        for b in buyer_records:
            product_statuses.append(
                StudentProductStatus(
                    product_name=products.get(b.hotmart_product_id, b.hotmart_product_id),
                    status=b.status,
                )
            )

        items.append(
            StudentListItem(
                email=email,
                name=name,
                phone=phone,
                discord_connected=user is not None and user.discord_id is not None,
                has_whatsapp=phone is not None and phone != "",
                has_account=user is not None,
                products=product_statuses,
            )
        )

    return StudentListResponse(items=items, total=total)


@router.post("/sync", response_model=SyncTriggerResponse, status_code=202)
def trigger_sync(
    body: SyncTriggerRequest = SyncTriggerRequest(),
    _: None = Depends(admin_only),
):
    """Trigger a full Hotmart sync. Returns task_id for polling."""
    from app.redis_client import get_redis_client

    redis = get_redis_client()

    # Check for concurrent sync
    if redis.get("sync:students:lock"):
        raise HTTPException(status_code=409, detail="A sync is already running")

    from app.tasks import sync_students_full
    task = sync_students_full.delay(body.product_id)

    return SyncTriggerResponse(task_id=task.id)


@router.get("/sync/{task_id}", response_model=SyncStatusResponse)
def get_sync_status(
    task_id: str,
    _: None = Depends(admin_only),
):
    """Poll sync status by task_id."""
    from app.redis_client import get_redis_client

    redis = get_redis_client()
    result = redis.get(f"sync:students:result:{task_id}")

    if not result:
        raise HTTPException(status_code=404, detail="Sync result not found or expired")

    return SyncStatusResponse(**json.loads(result))
