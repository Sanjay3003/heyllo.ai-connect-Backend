"""Calls API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Call, Lead, Campaign
from app.models.enums import CallStatus, CallOutcome
from app.schemas.call import CallCreate, CallUpdate, CallResponse, CallStats
from app.dependencies import get_current_tenant_id

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.get("", response_model=list[CallResponse])
async def get_calls(
    status_filter: Optional[CallStatus] = None,
    outcome_filter: Optional[CallOutcome] = None,
    campaign_id: Optional[UUID] = None,
    lead_id: Optional[UUID] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get all calls with optional filters"""
    
    query = db.query(Call).filter(Call.tenant_id == tenant_id)
    
    if status_filter:
        query = query.filter(Call.status == status_filter)
    
    if outcome_filter:
        query = query.filter(Call.outcome == outcome_filter)
    
    if campaign_id:
        query = query.filter(Call.campaign_id == campaign_id)
    
    if lead_id:
        query = query.filter(Call.lead_id == lead_id)
    
    calls = query.order_by(Call.created_at.desc()).all()
    
    return [CallResponse.from_orm(call) for call in calls]


@router.get("/active", response_model=list[CallResponse])
async def get_active_calls(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get currently active calls"""
    
    calls = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.status.in_([CallStatus.IN_PROGRESS, CallStatus.RINGING])
    ).all()
    
    return [CallResponse.from_orm(call) for call in calls]


@router.get("/queue", response_model=list[CallResponse])
async def get_queued_calls(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get pending/queued calls"""
    
    calls = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.status == CallStatus.PENDING
    ).order_by(Call.created_at).all()
    
    return [CallResponse.from_orm(call) for call in calls]


@router.get("/stats", response_model=CallStats)
async def get_call_stats(
    date_range: str = Query("7d", pattern="^(7d|30d|90d)$"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get call statistics"""
    
    # Calculate date range
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(date_range, 7)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query for date range
    base_query = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.created_at >= start_date
    )
    
    total_calls = base_query.count()
    
    active_calls = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.status == CallStatus.IN_PROGRESS
    ).count()
    
    ringing = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.status == CallStatus.RINGING
    ).count()
    
    queued = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.status == CallStatus.PENDING
    ).count()
    
    completed = base_query.filter(Call.status == CallStatus.COMPLETED).count()
    
    # Calculate answer rate
    answer_rate = (completed / total_calls * 100) if total_calls > 0 else 0
    
    # Calculate success rate (interested / completed)
    interested_count = base_query.filter(
        Call.status == CallStatus.COMPLETED,
        Call.outcome == CallOutcome.INTERESTED
    ).count()
    success_rate = (interested_count / completed * 100) if completed > 0 else 0
    
    # Calculate average duration
    avg_duration_result = base_query.filter(
        Call.status == CallStatus.COMPLETED
    ).with_entities(func.avg(Call.duration_seconds)).scalar()
    avg_duration_seconds = int(avg_duration_result) if avg_duration_result else 0
    
    return CallStats(
        total_calls=total_calls,
        active_calls=active_calls,
        ringing=ringing,
        queued=queued,
        completed=completed,
        answer_rate=round(answer_rate, 1),
        success_rate=round(success_rate, 1),
        avg_duration_seconds=avg_duration_seconds
    )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get a single call"""
    
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.tenant_id == tenant_id
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return CallResponse.from_orm(call)


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call_data: CallCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Initiate a new call"""
    
    # Verify lead belongs to tenant
    lead = db.query(Lead).filter(
        Lead.id == call_data.lead_id,
        Lead.tenant_id == tenant_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Create call
    new_call = Call(
        tenant_id=tenant_id,
        lead_id=call_data.lead_id,
        campaign_id=call_data.campaign_id,
        status=CallStatus.PENDING,
        started_at=datetime.utcnow()
    )
    db.add(new_call)
    db.commit()
    db.refresh(new_call)
    
    return CallResponse.from_orm(new_call)


@router.patch("/{call_id}/status", response_model=CallResponse)
async def update_call_status(
    call_id: UUID,
    call_update: CallUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update call status and outcome"""
    
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.tenant_id == tenant_id
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Update fields
    update_data = call_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(call, field, value)
    
    # Set ended_at if status is completed
    if call_update.status == CallStatus.COMPLETED and not call.ended_at:
        call.ended_at = datetime.utcnow()
    
    db.commit()
    db.refresh(call)
    
    return CallResponse.from_orm(call)
