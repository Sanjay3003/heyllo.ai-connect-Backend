"""Call schemas"""

from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime
from app.models.enums import CallStatus, CallOutcome


class CallBase(BaseModel):
    """Base call schema"""
    lead_id: UUID4
    campaign_id: Optional[UUID4] = None
    status: Optional[CallStatus] = CallStatus.PENDING
    outcome: Optional[CallOutcome] = None
    duration_seconds: Optional[int] = 0
    notes: Optional[str] = None


class CallCreate(BaseModel):
    """Schema for creating/initiating a call"""
    lead_id: UUID4
    campaign_id: Optional[UUID4] = None


class CallUpdate(BaseModel):
    """Schema for updating a call"""
    status: Optional[CallStatus] = None
    outcome: Optional[CallOutcome] = None
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None


class CallResponse(CallBase):
    """Schema for call response"""
    id: UUID4
    tenant_id: UUID4
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Bland AI Integration
    external_call_id: Optional[str] = None
    sentiment: Optional[str] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    cost: Optional[int] = 0
    
    class Config:
        from_attributes = True


class CallStats(BaseModel):
    """Call statistics schema"""
    total_calls: int
    active_calls: int
    ringing: int
    queued: int
    completed: int
    answer_rate: float
    success_rate: float
    avg_duration_seconds: int
