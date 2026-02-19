from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user, require_admin
from app.auth.security import hash_password, verify_password
from app.schemas.auth import UserResponse
from app.config import settings
from app.integrations import manychat

router = APIRouter(prefix="/users", tags=["Users"])


class UpdateProfileRequest(BaseModel):
    """Schema for profile update"""
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)
    whatsapp_number: Optional[str] = None


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat()
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile (email and/or password)"""

    # Update email if provided
    if update_data.email:
        # Check if email is already taken
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = update_data.email
        # TODO: Send verification email to new address

    # Update password if provided
    if update_data.new_password:
        if not update_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password required to set new password"
            )

        # Verify current password
        if not verify_password(update_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        current_user.password_hash = hash_password(update_data.new_password)

    if update_data.whatsapp_number:
        current_user.whatsapp_number = update_data.whatsapp_number
        if settings.manychat_enabled:
            subscriber_id = manychat.find_subscriber(update_data.whatsapp_number)
            if subscriber_id:
                current_user.manychat_subscriber_id = subscriber_id

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
        whatsapp_number=current_user.whatsapp_number,
        manychat_subscriber_id=current_user.manychat_subscriber_id,
    )


@router.get("", response_model=List[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role.value,
            created_at=u.created_at.isoformat()
        )
        for u in users
    ]
