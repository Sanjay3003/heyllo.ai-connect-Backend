"""AI Configuration model"""

from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class AIConfiguration(Base):
    """AI Configuration model for storing AI agent settings per tenant"""
    
    __tablename__ = "ai_configurations"
    
    # Use String(36) to match tenants.id type
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, unique=True)
    
    # Prompts
    system_prompt = Column(Text, nullable=True)
    opening_line = Column(String(500), nullable=True)
    
    # Voice Settings
    voice = Column(String(50), default="nat")  # nat, josh, florian, derek, june, paige
    speed = Column(String(20), default="normal")  # slow, normal, fast
    tone = Column(String(20), default="professional")  # professional, friendly, casual, formal
    language = Column(String(10), default="en-US")
    
    # Advanced Settings
    max_duration = Column(String(10), default="300")  # in seconds
    temperature = Column(String(10), default="0.7")
    wait_for_greeting = Column(String(10), default="true")
    record_calls = Column(String(10), default="true")
    
    # Intent Actions (JSON)
    intent_actions = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="ai_configuration")
