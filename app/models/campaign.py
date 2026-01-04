"""Campaign models"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import CampaignStatus


class Campaign(Base):
    """Campaign model"""
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Campaign Details
    name = Column(String, nullable=False)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="campaigns")
    calls = relationship("Call", back_populates="campaign")
    lead_associations = relationship("CampaignLead", back_populates="campaign")


class CampaignLead(Base):
    """Junction table for Campaign-Lead many-to-many relationship"""
    __tablename__ = "campaign_leads"
    
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), primary_key=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="lead_associations")
    lead = relationship("Lead", back_populates="campaign_associations")
