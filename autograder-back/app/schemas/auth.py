from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    whatsapp_number: Optional[str] = Field(None, description="E.164 format, e.g. +5511999999999")


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """Schema for user data response"""
    id: int
    email: str
    role: str
    created_at: str
    hotmart_id: Optional[str] = None
    discord_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    lifecycle_status: Optional[str] = None

    class Config:
        from_attributes = True
