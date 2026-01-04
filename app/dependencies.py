"""Shared dependencies for API routes"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import User, Profile
from app.utils.security import verify_token

# HTTP Bearer token security
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: The bearer token credentials
        db: Database session
        
    Returns:
        The authenticated User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UUID:
    """
    Get the tenant ID for the current user.
    
    Args:
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        The tenant UUID
        
    Raises:
        HTTPException: If user has no tenant
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile or not profile.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no tenant assigned"
        )
    
    return profile.tenant_id


def get_pagination_params(
    page: int = 1,
    limit: int = 50
) -> dict:
    """
    Get pagination parameters with validation.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
        
    Returns:
        Dictionary with skip and limit values
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100
    
    skip = (page - 1) * limit
    return {"skip": skip, "limit": limit, "page": page}
