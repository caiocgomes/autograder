"""Admin endpoints for managing lifecycle message templates."""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.models.message_template import MessageTemplate, TemplateEventType
from app.schemas.templates import TemplateOut, TemplateUpdateRequest, TEMPLATE_VARIABLES
from app.services.lifecycle import MSG_ONBOARDING, MSG_WELCOME, MSG_WELCOME_BACK, MSG_CHURN

router = APIRouter(prefix="/admin/templates", tags=["admin-templates"])

# Hardcoded defaults keyed by event_type value
DEFAULTS = {
    "onboarding": MSG_ONBOARDING,
    "welcome": MSG_WELCOME,
    "welcome_back": MSG_WELCOME_BACK,
    "churn": MSG_CHURN,
}

VALID_EVENT_TYPES = {"onboarding", "welcome", "welcome_back", "churn"}


def _event_type_enum(event_type_str: str) -> TemplateEventType:
    try:
        return TemplateEventType(event_type_str)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Tipo de evento inválido: {event_type_str}")


def _validate_template_vars(event_type_str: str, template_text: str) -> None:
    found = set(re.findall(r"\{(\w+)\}", template_text))
    allowed = TEMPLATE_VARIABLES.get(event_type_str, set())
    unknown = found - allowed
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Variáveis inválidas para {event_type_str}: {sorted(unknown)}. Permitidas: {sorted(allowed)}"
        )


@router.get("", response_model=List[TemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all lifecycle message templates (DB + defaults for missing)."""
    db_templates = db.query(MessageTemplate).all()
    db_map = {t.event_type.value: t for t in db_templates}

    result = []
    for event_type_str, default_text in DEFAULTS.items():
        if event_type_str in db_map:
            t = db_map[event_type_str]
            result.append(TemplateOut(
                event_type=event_type_str,
                template_text=t.template_text,
                is_default=False,
                updated_at=t.updated_at,
            ))
        else:
            result.append(TemplateOut(
                event_type=event_type_str,
                template_text=default_text,
                is_default=True,
                updated_at=None,
            ))
    return result


@router.patch("/{event_type}", response_model=TemplateOut)
def update_template(
    event_type: str,
    request: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create or update a lifecycle message template."""
    if event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo de evento inválido: {event_type}")

    _validate_template_vars(event_type, request.template_text)

    event_type_enum = _event_type_enum(event_type)
    existing = db.query(MessageTemplate).filter(MessageTemplate.event_type == event_type_enum).first()

    if existing:
        existing.template_text = request.template_text
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return TemplateOut(
            event_type=event_type,
            template_text=existing.template_text,
            is_default=False,
            updated_at=existing.updated_at,
        )
    else:
        template = MessageTemplate(
            event_type=event_type_enum,
            template_text=request.template_text,
            updated_by=current_user.id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return TemplateOut(
            event_type=event_type,
            template_text=template.template_text,
            is_default=False,
            updated_at=template.updated_at,
        )


@router.delete("/{event_type}", response_model=TemplateOut)
def delete_template(
    event_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a template, reverting to hardcoded default."""
    if event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo de evento inválido: {event_type}")

    event_type_enum = _event_type_enum(event_type)
    existing = db.query(MessageTemplate).filter(MessageTemplate.event_type == event_type_enum).first()

    if existing:
        db.delete(existing)
        db.commit()

    return TemplateOut(
        event_type=event_type,
        template_text=DEFAULTS[event_type],
        is_default=True,
        updated_at=None,
    )
