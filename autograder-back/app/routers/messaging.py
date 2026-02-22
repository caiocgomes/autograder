from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional, List

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer
from app.models.hotmart_product_mapping import HotmartProductMapping
from app.models.message_campaign import (
    MessageCampaign,
    MessageRecipient,
    CampaignStatus,
    RecipientStatus,
)
from app.schemas.messaging import (
    CourseOut,
    RecipientOut,
    BulkSendRequest,
    BulkSendResponse,
    SkippedUser,
    CampaignOut,
    CampaignDetailOut,
    RecipientStatusOut,
    RetryResponse,
)
from app.celery_app import celery_app

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.get("/courses", response_model=List[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List courses available for messaging (products that are targets in hotmart_product_mapping)."""
    target_id_rows = db.query(distinct(HotmartProductMapping.target_product_id)).all()
    target_ids = [row[0] for row in target_id_rows]
    if not target_ids:
        return []
    courses = (
        db.query(Product)
        .filter(Product.id.in_(target_ids))
        .order_by(Product.name)
        .all()
    )
    return [CourseOut(id=c.id, name=c.name) for c in courses]


@router.get("/recipients", response_model=List[RecipientOut])
def list_recipients(
    course_id: int = Query(...),
    has_whatsapp: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List students of a course (people who bought any product that maps to this course)."""
    course = db.query(Product).filter(Product.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    source_ids = (
        db.query(HotmartProductMapping.source_hotmart_product_id)
        .filter(HotmartProductMapping.target_product_id == course_id)
        .all()
    )
    hotmart_product_ids = [row[0] for row in source_ids]

    if not hotmart_product_ids:
        return []

    query = (
        db.query(User, HotmartBuyer.name.label("buyer_name"))
        .join(HotmartBuyer, HotmartBuyer.user_id == User.id)
        .filter(HotmartBuyer.hotmart_product_id.in_(hotmart_product_ids))
    )

    if has_whatsapp is True:
        query = query.filter(User.whatsapp_number.isnot(None), User.whatsapp_number != "")
    elif has_whatsapp is False:
        query = query.filter((User.whatsapp_number.is_(None)) | (User.whatsapp_number == ""))

    rows = query.order_by(User.id).all()

    seen = set()
    recipients = []
    for user, buyer_name in rows:
        if user.id in seen:
            continue
        seen.add(user.id)
        display_name = buyer_name if buyer_name else user.email
        recipients.append(
            RecipientOut(
                id=user.id,
                name=display_name,
                email=user.email,
                whatsapp_number=user.whatsapp_number,
                has_whatsapp=bool(user.whatsapp_number),
            )
        )

    return recipients


@router.get("/campaigns", response_model=List[CampaignOut])
def list_campaigns(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List message campaigns with pagination and optional status filter."""
    query = db.query(MessageCampaign)

    if status_filter:
        try:
            campaign_status = CampaignStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Status inválido: {status_filter}")
        query = query.filter(MessageCampaign.status == campaign_status)

    campaigns = (
        query
        .order_by(MessageCampaign.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        CampaignOut(
            id=c.id,
            message_template=c.message_template,
            course_name=c.course_name,
            total_recipients=c.total_recipients,
            sent_count=c.sent_count,
            failed_count=c.failed_count,
            status=c.status.value,
            created_at=c.created_at,
            completed_at=c.completed_at,
        )
        for c in campaigns
    ]


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailOut)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get campaign detail with recipient status list."""
    campaign = db.query(MessageCampaign).filter(MessageCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    recipients = (
        db.query(MessageRecipient)
        .filter(MessageRecipient.campaign_id == campaign_id)
        .order_by(MessageRecipient.id)
        .all()
    )

    return CampaignDetailOut(
        id=campaign.id,
        message_template=campaign.message_template,
        course_name=campaign.course_name,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        status=campaign.status.value,
        created_at=campaign.created_at,
        completed_at=campaign.completed_at,
        recipients=[
            RecipientStatusOut(
                user_id=r.user_id,
                name=r.name,
                phone=r.phone,
                status=r.status.value,
                resolved_message=r.resolved_message,
                sent_at=r.sent_at,
                error_message=r.error_message,
            )
            for r in recipients
        ],
    )


@router.post(
    "/campaigns/{campaign_id}/retry",
    response_model=RetryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Retry failed recipients in a campaign."""
    campaign = db.query(MessageCampaign).filter(MessageCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    if campaign.status == CampaignStatus.SENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campanha ainda está sendo processada",
        )

    failed_recipients = (
        db.query(MessageRecipient)
        .filter(
            MessageRecipient.campaign_id == campaign_id,
            MessageRecipient.status == RecipientStatus.FAILED,
        )
        .all()
    )

    if not failed_recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum destinatário falhado para reenviar",
        )

    # Reset failed recipients to pending
    for r in failed_recipients:
        r.status = RecipientStatus.PENDING
        r.error_message = None

    campaign.status = CampaignStatus.SENDING
    campaign.failed_count = 0
    campaign.completed_at = None

    db.commit()

    # Dispatch task for pending recipients only
    celery_app.send_task(
        "app.tasks.send_bulk_messages",
        args=[campaign.id, campaign.message_template],
        kwargs={"only_pending": True},
    )

    return RetryResponse(retrying=len(failed_recipients), campaign_id=campaign.id)


@router.post("/send", response_model=BulkSendResponse, status_code=status.HTTP_202_ACCEPTED)
def send_bulk_message(
    request: BulkSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Dispatch bulk WhatsApp message to selected students via Celery."""
    users = db.query(User).filter(User.id.in_(request.user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado")

    # Resolve course name for {turma} variable
    course_name = ""
    if request.course_id:
        course = db.query(Product).filter(Product.id == request.course_id).first()
        if course:
            course_name = course.name

    # Get buyer names for these users (best-effort)
    buyer_names = {}
    if request.user_ids:
        buyers = (
            db.query(HotmartBuyer.user_id, HotmartBuyer.name)
            .filter(HotmartBuyer.user_id.in_(request.user_ids), HotmartBuyer.name.isnot(None))
            .all()
        )
        for user_id, name in buyers:
            if name and user_id not in buyer_names:
                buyer_names[user_id] = name

    # Split into sendable vs skipped
    sendable = []
    skipped = []
    for user in users:
        if not user.whatsapp_number:
            skipped.append(SkippedUser(id=user.id, name=user.email, reason="no_whatsapp"))
        else:
            display_name = buyer_names.get(user.id, user.email)
            sendable.append({
                "user_id": user.id,
                "phone": user.whatsapp_number,
                "name": display_name,
                "email": user.email,
            })

    if not sendable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum destinatário com WhatsApp disponível",
        )

    # Create campaign
    campaign = MessageCampaign(
        message_template=request.message_template,
        course_id=request.course_id,
        course_name=course_name or None,
        sent_by=current_user.id,
        status=CampaignStatus.SENDING,
        total_recipients=len(sendable),
    )
    db.add(campaign)
    db.flush()  # get campaign.id

    # Create recipient records
    for r in sendable:
        recipient = MessageRecipient(
            campaign_id=campaign.id,
            user_id=r["user_id"],
            phone=r["phone"],
            name=r["name"],
            status=RecipientStatus.PENDING,
        )
        db.add(recipient)

    db.commit()
    db.refresh(campaign)

    # Dispatch Celery task
    task = celery_app.send_task(
        "app.tasks.send_bulk_messages",
        args=[campaign.id, request.message_template],
    )

    return BulkSendResponse(
        campaign_id=campaign.id,
        task_id=task.id,
        total_recipients=len(sendable),
        skipped_no_phone=len(skipped),
        skipped_users=skipped,
    )
