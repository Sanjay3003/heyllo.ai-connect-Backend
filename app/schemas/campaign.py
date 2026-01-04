"""Campaign schemas"""

from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime, date
from app.models.enums import CampaignStatus


class CampaignBase(BaseModel):
    """Base campaign schema"""
    name: str
    status: Optional[CampaignStatus] = CampaignStatus.DRAFT
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    lead_ids: Optional[List[UUID4]] = []


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignResponse(CampaignBase):
    """Schema for campaign response"""
    id: UUID4
    tenant_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CampaignStats(BaseModel):
    """Campaign statistics schema"""
    total_leads: int
    called: int
    answered: int
    interested: int
    conversion_rate: float
    progress_percentage: float
