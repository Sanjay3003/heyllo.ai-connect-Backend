"""Analytics API routes"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.models import Call, Campaign
from app.models.enums import CallStatus, CallOutcome
from app.schemas.analytics import (
    DashboardKPIs,
    CallsOverTime,
    OutcomeDistribution,
    CampaignPerformance
)
from app.dependencies import get_current_tenant_id

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardKPIs)
async def get_dashboard_kpis(
    date_range: str = Query("7d", pattern="^(7d|30d|90d)$"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get dashboard KPI metrics"""
    
    # Calculate date range
    days_map = {"7d": 7, "30d":30, "90d": 90}
    days = days_map.get(date_range, 7)
    current_start = datetime.utcnow() - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    
    # Current period stats
    current_calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.created_at >= current_start
    )
    
    total_calls = current_calls.count()
    completed_calls = current_calls.filter(Call.status == CallStatus.COMPLETED).count()
    answer_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
    
    interested_leads = current_calls.filter(
        Call.outcome == CallOutcome.INTERESTED
    ).count()
    
    # Average duration
    avg_duration_result = current_calls.filter(
        Call.status == CallStatus.COMPLETED
    ).with_entities(func.avg(Call.duration_seconds)).scalar()
    avg_seconds = int(avg_duration_result) if avg_duration_result else 0
    avg_duration = f"{avg_seconds // 60}:{avg_seconds % 60:02d}"
    
    # Mock cost per lead (you can calculate this based on your pricing)
    cost_per_lead = 1.24
    
    # Previous period for trends
    previous_calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.created_at >= previous_start,
        Call.created_at < current_start
    ).count()
    
    previous_completed = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.created_at >= previous_start,
        Call.created_at < current_start,
        Call.status == CallStatus.COMPLETED
    ).count()
    
    previous_answer_rate = (previous_completed / previous_calls * 100) if previous_calls > 0 else 0
    
    # Calculate changes
    total_calls_change = ((total_calls - previous_calls) / previous_calls * 100) if previous_calls > 0 else 0
    answer_rate_change = answer_rate - previous_answer_rate
    
    return DashboardKPIs(
        total_calls=total_calls,
        answer_rate=round(answer_rate, 1),
        interested_leads=interested_leads,
        avg_duration=avg_duration,
        cost_per_lead=cost_per_lead,
        total_calls_change=round(total_calls_change, 1),
        answer_rate_change=round(answer_rate_change, 1)
    )


@router.get("/calls-overtime", response_model=List[CallsOverTime])
async def get_calls_overtime(
    date_range: str = Query("7d"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get time series data for call volume"""
    
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(date_range, 7)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query calls grouped by date
    results = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_calls = db.query(Call).filter(
            Call.tenant_id == str(tenant_id),
            Call.created_at >= day_start,
            Call.created_at < day_end
        )
        
        total = day_calls.count()
        answered = day_calls.filter(Call.status == CallStatus.COMPLETED).count()
        interested = day_calls.filter(Call.outcome == CallOutcome.INTERESTED).count()
        
        results.append(CallsOverTime(
            date=day_start.strftime("%a"),
            calls=total,
            answered=answered,
            interested=interested
        ))
    
    return results


@router.get("/outcomes", response_model=List[OutcomeDistribution])
async def get_outcome_distribution(
    date_range: str = Query("7d"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get call outcome distribution"""
    
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(date_range, 7)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get total completed calls
    total_calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.created_at >= start_date,
        Call.status == CallStatus.COMPLETED
    ).count()
    
    # Get counts by outcome
    outcomes = db.query(
        Call.outcome,
        func.count(Call.id).label('count')
    ).filter(
        Call.tenant_id == str(tenant_id),
        Call.created_at >= start_date,
        Call.status == CallStatus.COMPLETED,
        Call.outcome.isnot(None)
    ).group_by(Call.outcome).all()
    
    results = []
    for outcome, count in outcomes:
        percentage = (count / total_calls * 100) if total_calls > 0 else 0
        results.append(OutcomeDistribution(
            outcome=outcome.value,
            count=count,
            percentage=round(percentage, 1)
        ))
    
    return results


@router.get("/campaigns-performance", response_model=List[CampaignPerformance])
async def get_campaigns_performance(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get campaign performance metrics"""
    
    campaigns = db.query(Campaign).filter(
        Campaign.tenant_id == str(tenant_id)
    ).all()
    
    results = []
    for campaign in campaigns:
        campaign_calls = db.query(Call).filter(
            Call.campaign_id == campaign.id
        )
        
        total_calls = campaign_calls.count()
        answered = campaign_calls.filter(Call.status == CallStatus.COMPLETED).count()
        interested = campaign_calls.filter(Call.outcome == CallOutcome.INTERESTED).count()
        
        conversion_rate = (interested / total_calls * 100) if total_calls > 0 else 0
        
        results.append(CampaignPerformance(
            name=campaign.name,
            total_calls=total_calls,
            answered=answered,
            interested=interested,
            conversion_rate=round(conversion_rate, 1),
            cost_per_lead=2.34  # Mock data
        ))
    
    return results
