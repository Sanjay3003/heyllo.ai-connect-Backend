"""AI Configuration API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import AIConfiguration
from app.schemas.ai_config import AIConfigCreate, AIConfigUpdate, AIConfigResponse
from app.dependencies import get_current_tenant_id, get_current_user
from app.models import User

router = APIRouter(prefix="/api/ai-config", tags=["AI Configuration"])


@router.get("", response_model=AIConfigResponse)
async def get_ai_config(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get AI configuration for the current tenant"""
    
    config = db.query(AIConfiguration).filter(
        AIConfiguration.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Return default config if none exists
        config = AIConfiguration(
            tenant_id=tenant_id,
            system_prompt="",
            opening_line="",
            voice="nat",
            speed="normal",
            tone="professional",
            language="en-US",
            max_duration="300",
            temperature="0.7",
            wait_for_greeting="true",
            record_calls="true",
            intent_actions={
                "interested": {"action": "transfer_to_sales", "enabled": True},
                "not_interested": {"action": "log_and_end", "enabled": True},
                "callback": {"action": "schedule_followup", "enabled": True},
                "wrong_number": {"action": "mark_invalid", "enabled": True},
            }
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return AIConfigResponse.from_orm(config)


@router.post("", response_model=AIConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_config(
    config_data: AIConfigCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create AI configuration for tenant"""
    
    # Check if config already exists
    existing = db.query(AIConfiguration).filter(
        AIConfiguration.tenant_id == tenant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="AI configuration already exists. Use PATCH to update."
        )
    
    # Create new config
    config = AIConfiguration(
        tenant_id=tenant_id,
        **config_data.model_dump()
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return AIConfigResponse.from_orm(config)


@router.patch("", response_model=AIConfigResponse)
async def update_ai_config(
    config_data: AIConfigUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update AI configuration"""
    
    config = db.query(AIConfiguration).filter(
        AIConfiguration.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Create new config with updates
        config = AIConfiguration(
            tenant_id=tenant_id,
            **config_data.model_dump(exclude_unset=True)
        )
        db.add(config)
    else:
        # Update existing config
        update_data = config_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        config.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(config)
    
    return AIConfigResponse.from_orm(config)


@router.put("", response_model=AIConfigResponse)
async def replace_ai_config(
    config_data: AIConfigCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Replace entire AI configuration"""
    
    config = db.query(AIConfiguration).filter(
        AIConfiguration.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Create new
        config = AIConfiguration(
            tenant_id=tenant_id,
            **config_data.model_dump()
        )
        db.add(config)
    else:
        # Replace all fields
        for field, value in config_data.model_dump().items():
            setattr(config, field, value)
        config.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(config)
    
    return AIConfigResponse.from_orm(config)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_config(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Delete AI configuration (resets to defaults)"""
    
    config = db.query(AIConfiguration).filter(
        AIConfiguration.tenant_id == tenant_id
    ).first()
    
    if config:
        db.delete(config)
        db.commit()
    
    return None
