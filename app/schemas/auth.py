"""Authentication schemas"""

from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID4
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    tenant_id: Optional[UUID4] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored in JWT token"""
    user_id: Optional[UUID4] = None
    email: Optional[str] = None
    tenant_id: Optional[UUID4] = None
