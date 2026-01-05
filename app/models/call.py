"""Call model"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import CallStatus, CallOutcome


class Call(Base):
    """Call record model"""
    __tablename__ = "calls"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True, index=True)
    
    # Call Details
    status = Column(SQLEnum(CallStatus), default=CallStatus.PENDING, nullable=False, index=True)
    outcome = Column(SQLEnum(CallOutcome), nullable=True)
    duration_seconds = Column(Integer, default=0)
    notes = Column(Text)
    
    # Bland AI Integration
    external_call_id = Column(String(100), nullable=True, unique=True, index=True)  # Bland AI call ID
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    transcript = Column(Text, nullable=True)  # JSON transcript from Bland
    recording_url = Column(String(500), nullable=True)  # Audio recording URL
    cost = Column(Integer, default=0)  # Cost in cents
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="calls")
    lead = relationship("Lead", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")
