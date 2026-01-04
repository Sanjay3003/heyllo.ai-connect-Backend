"""Lead model"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import LeadStatus


class Lead(Base):
    """Lead/Contact model"""
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Contact Information
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, index=True)
    phone = Column(String, nullable=False, index=True)
    company = Column(String)
    
    # Status
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="leads")
    calls = relationship("Call", back_populates="lead")
    campaign_associations = relationship("CampaignLead", back_populates="lead")
