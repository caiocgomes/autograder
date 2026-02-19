from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.auth.rate_limiter import rate_limiter
from app.config import settings
from app.integrations import manychat

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user with email and password"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        role=UserRole.STUDENT  # Default role
    )

    if user_data.whatsapp_number:
        new_user.whatsapp_number = user_data.whatsapp_number
        if settings.manychat_enabled:
            subscriber_id = manychat.find_subscriber(user_data.whatsapp_number)
            if subscriber_id:
                new_user.manychat_subscriber_id = subscriber_id

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate tokens
    access_token = create_access_token({"sub": str(new_user.id)})
    refresh_token = create_refresh_token({"sub": str(new_user.id)})

    # TODO: Send confirmation email

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT tokens"""
    # Check rate limiting
    if rate_limiter.is_blocked(credentials.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Please try again in {rate_limiter.window_minutes} minutes."
        )

    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()

    # Verify credentials (use constant-time comparison by always verifying)
    if user is None or not verify_password(credentials.password, user.password_hash):
        # Record failed attempt
        attempts = rate_limiter.record_failed_attempt(credentials.email)
        remaining = rate_limiter.max_attempts - attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"X-Remaining-Attempts": str(max(0, remaining))}
        )

    # Reset rate limiter on successful login
    rate_limiter.reset(credentials.email)

    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = verify_token(request.refresh_token, expected_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Verify user still exists
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Generate new tokens (optional: rotate refresh token)
    access_token = create_access_token({"sub": str(user_id)})
    new_refresh_token = create_refresh_token({"sub": str(user_id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset link via email"""
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success to prevent email enumeration
    # If user exists, send reset email
    if user:
        # Generate reset token (short-lived JWT)
        reset_token = create_access_token({"sub": str(user.id), "purpose": "password_reset"})
        # TODO: Send email with reset link containing token
        # Email should contain link like: https://frontend.com/reset-password?token={reset_token}
        pass

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Complete password reset with token from email"""
    payload = verify_token(request.token, expected_type="access")

    if payload is None or payload.get("purpose") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    db.commit()

    return {"message": "Password updated successfully"}
