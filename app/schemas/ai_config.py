"""AI Configuration schemas"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class IntentAction(BaseModel):
    """Intent action configuration"""
    intent: str
    action: str
    enabled: bool = True


class AIConfigBase(BaseModel):
    """Base AI Configuration schema"""
    system_prompt: Optional[str] = None
    opening_line: Optional[str] = None
    voice: str = "nat"
    speed: str = "normal"
    tone: str = "professional"
    language: str = "en-US"
    max_duration: str = "300"
    temperature: str = "0.7"
    wait_for_greeting: str = "true"
    record_calls: str = "true"
    intent_actions: Optional[Dict[str, Any]] = None


class AIConfigCreate(AIConfigBase):
    """Schema for creating AI Configuration"""
    pass


class AIConfigUpdate(BaseModel):
    """Schema for updating AI Configuration"""
    system_prompt: Optional[str] = None
    opening_line: Optional[str] = None
    voice: Optional[str] = None
    speed: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None
    max_duration: Optional[str] = None
    temperature: Optional[str] = None
    wait_for_greeting: Optional[str] = None
    record_calls: Optional[str] = None
    intent_actions: Optional[Dict[str, Any]] = None


class AIConfigResponse(AIConfigBase):
    """Response schema for AI Configuration"""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        orm_mode = True
