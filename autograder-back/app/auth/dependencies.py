from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.auth.security import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token, expected_type="access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is active (for future use if we add deactivation)"""
    return current_user


def require_role(*allowed_roles: UserRole):
    """Factory to create role-based access control dependency"""
    # Flatten if called with a list/tuple as single argument: require_role([A, B])
    flat_roles = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple)):
            flat_roles.extend(r)
        else:
            flat_roles.append(r)

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in flat_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(r.value for r in flat_roles)}"
            )
        return current_user
    return role_checker


# Convenience dependencies for common role checks
require_admin = require_role(UserRole.ADMIN)
require_professor = require_role(UserRole.PROFESSOR, UserRole.ADMIN)
require_student = require_role(UserRole.STUDENT)
