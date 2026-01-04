"""Lead schemas"""

from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional, List
from datetime import datetime
from app.models.enums import LeadStatus


class LeadBase(BaseModel):
    """Base lead schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: str
    company: Optional[str] = None
    status: Optional[LeadStatus] = LeadStatus.NEW


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    pass


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: UUID4
    tenant_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list"""
    total: int
    page: int
    page_size: int
    leads: List[LeadResponse]
