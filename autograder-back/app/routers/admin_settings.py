"""Admin-only endpoints for managing system settings (LLM API tokens)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.models.system_settings import SystemSettings
from app.schemas.system_settings import (
    SystemSettingsUpdate,
    SystemSettingsResponse,
    mask_token,
)
from app.services.encryption import encrypt_value, decrypt_value

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get current system settings with masked token values."""
    row = db.query(SystemSettings).first()
    if not row:
        return SystemSettingsResponse()

    openai_decrypted = decrypt_value(row.openai_api_key_encrypted or "")
    anthropic_decrypted = decrypt_value(row.anthropic_api_key_encrypted or "")

    return SystemSettingsResponse(
        openai_api_key_masked=mask_token(openai_decrypted),
        anthropic_api_key_masked=mask_token(anthropic_decrypted),
        openai_configured=bool(openai_decrypted),
        anthropic_configured=bool(anthropic_decrypted),
    )


@router.put("", response_model=SystemSettingsResponse)
def update_settings(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update system settings. Only provided fields are changed."""
    row = db.query(SystemSettings).first()

    if not row:
        row = SystemSettings(updated_by=current_user.id)
        db.add(row)

    if payload.openai_api_key is not None:
        row.openai_api_key_encrypted = encrypt_value(payload.openai_api_key) if payload.openai_api_key else None
    if payload.anthropic_api_key is not None:
        row.anthropic_api_key_encrypted = encrypt_value(payload.anthropic_api_key) if payload.anthropic_api_key else None

    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)

    openai_decrypted = decrypt_value(row.openai_api_key_encrypted or "")
    anthropic_decrypted = decrypt_value(row.anthropic_api_key_encrypted or "")

    return SystemSettingsResponse(
        openai_api_key_masked=mask_token(openai_decrypted),
        anthropic_api_key_masked=mask_token(anthropic_decrypted),
        openai_configured=bool(openai_decrypted),
        anthropic_configured=bool(anthropic_decrypted),
    )
