from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import distinct, select
from typing import Optional, List

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.hotmart_buyer import HotmartBuyer
from app.models.hotmart_product_mapping import HotmartProductMapping
from app.schemas.messaging import CourseOut, RecipientOut, BulkSendRequest, BulkSendResponse, SkippedUser
from app.celery_app import celery_app

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.get("/courses", response_model=List[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List courses available for messaging (products that are targets in hotmart_product_mapping)."""
    # Courses = products that appear as targets in the mapping (not bundles like "A Base de Tudo")
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
    # Verify course exists
    course = db.query(Product).filter(Product.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    # Find all Hotmart product IDs that map to this course
    source_ids = (
        db.query(HotmartProductMapping.source_hotmart_product_id)
        .filter(HotmartProductMapping.target_product_id == course_id)
        .all()
    )
    hotmart_product_ids = [row[0] for row in source_ids]

    if not hotmart_product_ids:
        return []

    # Find users who bought any of these products (via hotmart_buyers with user_id set)
    query = (
        db.query(User, HotmartBuyer.name.label("buyer_name"))
        .join(HotmartBuyer, HotmartBuyer.user_id == User.id)
        .filter(HotmartBuyer.hotmart_product_id.in_(hotmart_product_ids))
    )

    # Optional WhatsApp filter
    if has_whatsapp is True:
        query = query.filter(User.whatsapp_number.isnot(None), User.whatsapp_number != "")
    elif has_whatsapp is False:
        query = query.filter((User.whatsapp_number.is_(None)) | (User.whatsapp_number == ""))

    rows = query.order_by(User.id).all()

    # Deduplicate by user_id (a user might appear via multiple products)
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


@router.post("/send", response_model=BulkSendResponse, status_code=status.HTTP_202_ACCEPTED)
def send_bulk_message(
    request: BulkSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Dispatch bulk WhatsApp message to selected students via Celery."""
    # Load users
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
    recipients = []
    skipped = []
    for user in users:
        if not user.whatsapp_number:
            skipped.append(SkippedUser(id=user.id, name=user.email, reason="no_whatsapp"))
        else:
            display_name = buyer_names.get(user.id, user.email)
            recipients.append({
                "user_id": user.id,
                "phone": user.whatsapp_number,
                "name": display_name,
                "email": user.email,
                "class_name": course_name,
            })

    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum destinatário com WhatsApp disponível",
        )

    # Dispatch Celery task
    task = celery_app.send_task(
        "app.tasks.send_bulk_messages",
        args=[recipients, request.message_template],
    )

    return BulkSendResponse(
        task_id=task.id,
        total_recipients=len(recipients),
        skipped_no_phone=len(skipped),
        skipped_users=skipped,
    )
