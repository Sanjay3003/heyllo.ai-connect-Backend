"""Campaigns API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models import Campaign, CampaignLead, Lead, Call
from app.models.enums import CampaignStatus, CallOutcome
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignStats
from app.dependencies import get_current_tenant_id

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])


@router.get("", response_model=list[CampaignResponse])
async def get_campaigns(
    status_filter: Optional[CampaignStatus] = None,
    search: Optional[str] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get all campaigns for the tenant"""
    
    query = db.query(Campaign).filter(Campaign.tenant_id == tenant_id)
    
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    
    if search:
        query = query.filter(Campaign.name.ilike(f"%{search}%"))
    
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    
    return [CampaignResponse.from_orm(c) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get a single campaign"""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return CampaignResponse.from_orm(campaign)


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create a new campaign"""
    
    # Create campaign
    campaign_dict = campaign_data.model_dump(exclude={'lead_ids'})
    new_campaign = Campaign(
        **campaign_dict,
        tenant_id=tenant_id
    )
    db.add(new_campaign)
    db.flush()
    
    # Add leads to campaign
    if campaign_data.lead_ids:
        for lead_id in campaign_data.lead_ids:
            # Verify lead belongs to tenant
            lead = db.query(Lead).filter(
                Lead.id == lead_id,
                Lead.tenant_id == tenant_id
            ).first()
            
            if lead:
                campaign_lead = CampaignLead(
                    campaign_id=new_campaign.id,
                    lead_id=lead_id
                )
                db.add(campaign_lead)
    
    db.commit()
    db.refresh(new_campaign)
    
    return CampaignResponse.from_orm(new_campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update a campaign"""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = campaign_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    db.commit()
    db.refresh(campaign)
    
    return CampaignResponse.from_orm(campaign)


@router.patch("/{campaign_id}/status", response_model=CampaignResponse)
async def update_campaign_status(
    campaign_id: UUID,
    new_status: CampaignStatus,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update campaign status"""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.status = new_status
    db.commit()
    db.refresh(campaign)
    
    return CampaignResponse.from_orm(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Delete a campaign"""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    db.delete(campaign)
    db.commit()
    
    return None


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get campaign statistics"""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Count total leads in campaign
    total_leads = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id
    ).count()
    
    # Count calls made
    called = db.query(Call).filter(
        Call.campaign_id == campaign_id
    ).count()
    
    # Count answered calls (not pending or failed)
    answered = db.query(Call).filter(
        Call.campaign_id == campaign_id,
        Call.status == "completed"
    ).count()
    
    # Count interested leads
    interested = db.query(Call).filter(
        Call.campaign_id == campaign_id,
        Call.outcome == CallOutcome.INTERESTED
    ).count()
    
    # Calculate rates
    conversion_rate = (interested / called * 100) if called > 0 else 0
    progress_percentage = (called / total_leads * 100) if total_leads > 0 else 0
    
    return CampaignStats(
        total_leads=total_leads,
        called=called,
        answered=answered,
        interested=interested,
        conversion_rate=round(conversion_rate, 1),
        progress_percentage=round(progress_percentage, 1)
    )
