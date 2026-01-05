"""Tenant model"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Tenant(Base):
    """Tenant/Organization model"""
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="Basic")  # e.g., "Enterprise", "Business", "Basic"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    profiles = relationship("Profile", back_populates="tenant")
    leads = relationship("Lead", back_populates="tenant")
    campaigns = relationship("Campaign", back_populates="tenant")
    calls = relationship("Call", back_populates="tenant")
