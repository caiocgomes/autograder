"""Onboarding dashboard endpoints — student listing and funnel summary."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole, LifecycleStatus
from app.models.hotmart_buyer import HotmartBuyer
from app.models.message_campaign import MessageRecipient, RecipientStatus
from app.schemas.onboarding import OnboardingStudentOut, OnboardingSummaryOut

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

PENDING_STATUSES = [LifecycleStatus.PENDING_ONBOARDING, LifecycleStatus.PENDING_PAYMENT]


def _compute_token_status(user, now=None):
    """Compute token status from user fields."""
    if now is None:
        now = datetime.now(timezone.utc)

    if user.lifecycle_status == LifecycleStatus.ACTIVE:
        return "activated", None

    if user.onboarding_token is None:
        return "none", None

    if user.onboarding_token_expires_at and user.onboarding_token_expires_at < now:
        return "expired", None

    if user.onboarding_token_expires_at:
        days = (user.onboarding_token_expires_at - now).days
        return "valid", max(days, 0)

    return "valid", None


@router.get("/students", response_model=List[OnboardingStudentOut])
def list_onboarding_students(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List students with onboarding/token info for the dashboard."""
    # Build query: user + buyer name + last message timestamp
    last_msg = (
        db.query(
            MessageRecipient.user_id,
            func.max(MessageRecipient.sent_at).label("last_sent")
        )
        .filter(MessageRecipient.status == RecipientStatus.SENT)
        .group_by(MessageRecipient.user_id)
        .subquery()
    )

    query = (
        db.query(User, HotmartBuyer.name.label("buyer_name"), last_msg.c.last_sent)
        .outerjoin(HotmartBuyer, HotmartBuyer.email == User.email)
        .outerjoin(last_msg, last_msg.c.user_id == User.id)
    )

    # Filter to lifecycle-managed students
    query = query.filter(User.lifecycle_status.isnot(None))

    if course_id:
        from app.models.hotmart_product_mapping import HotmartProductMapping
        query = query.join(
            HotmartProductMapping,
            HotmartProductMapping.hotmart_product_id == HotmartBuyer.hotmart_product_id
        ).filter(HotmartProductMapping.product_id == course_id)

    # Order: pending first, then active
    query = query.group_by(User.id, HotmartBuyer.name, last_msg.c.last_sent).order_by(
        case(
            (User.lifecycle_status == LifecycleStatus.PENDING_ONBOARDING, 0),
            (User.lifecycle_status == LifecycleStatus.PENDING_PAYMENT, 1),
            (User.lifecycle_status == LifecycleStatus.CHURNED, 2),
            else_=3,
        ),
        User.email,
    )

    rows = query.all()
    now = datetime.now(timezone.utc)
    result = []
    for user, buyer_name, last_sent in rows:
        token_status, expires_in_days = _compute_token_status(user, now)
        result.append(OnboardingStudentOut(
            id=user.id,
            name=buyer_name or user.email.split("@")[0],
            email=user.email,
            whatsapp_number=user.whatsapp_number,
            lifecycle_status=user.lifecycle_status.value if user.lifecycle_status else None,
            token_status=token_status,
            token_expires_in_days=expires_in_days,
            last_message_at=last_sent,
        ))
    return result


@router.get("/summary", response_model=OnboardingSummaryOut)
def get_onboarding_summary(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get funnel counts for onboarding dashboard."""
    base_query = db.query(User).filter(User.lifecycle_status.isnot(None))

    if course_id:
        from app.models.hotmart_product_mapping import HotmartProductMapping
        base_query = (
            base_query
            .join(HotmartBuyer, HotmartBuyer.email == User.email)
            .join(HotmartProductMapping, HotmartProductMapping.hotmart_product_id == HotmartBuyer.hotmart_product_id)
            .filter(HotmartProductMapping.product_id == course_id)
        )

    total = base_query.count()
    activated = base_query.filter(User.lifecycle_status == LifecycleStatus.ACTIVE).count()
    pending = base_query.filter(User.lifecycle_status.in_(PENDING_STATUSES)).count()
    no_whatsapp = (
        base_query
        .filter(User.lifecycle_status.in_(PENDING_STATUSES))
        .filter(User.whatsapp_number.is_(None))
        .count()
    )

    return OnboardingSummaryOut(
        total=total,
        activated=activated,
        pending=pending,
        no_whatsapp=no_whatsapp,
    )
