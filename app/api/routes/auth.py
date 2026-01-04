"""Authentication API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import User, Profile, Tenant
from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )
    db.add(new_user)
    db.flush()
    
    # Create default tenant for the user
    tenant = Tenant(name=f"{user_data.full_name}'s Organization")
    db.add(tenant)
    db.flush()
    
    # Create profile linking user to tenant
    profile = Profile(user_id=new_user.id, tenant_id=tenant.id)
    db.add(profile)
    
    db.commit()
    
    # Generate tokens
    token_data = {
        "user_id": str(new_user.id),
        "email": new_user.email,
        "tenant_id": str(tenant.id),
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Get tenant ID
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    tenant_id = str(profile.tenant_id) if profile else None
    
    # Generate tokens
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "tenant_id": tenant_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        tenant_id=profile.tenant_id if profile else None,
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""
    
    # Verify refresh token
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Generate new access token
    token_data = {
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id"),
    }
    new_access_token = create_access_token(token_data)
    
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should remove tokens)"""
    return {"message": "Successfully logged out"}
