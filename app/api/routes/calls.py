"""Calls API routes with Bland AI + OpenAI Integration"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os

from app.database import get_db
from app.models import Call, Lead, Campaign
from app.models.enums import CallStatus, CallOutcome
from app.schemas.call import CallCreate, CallUpdate, CallResponse, CallStats
from app.dependencies import get_current_tenant_id, get_current_user
from app.models import User
from app.services.bland_client import bland_client

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


class InitiateCallRequest(BaseModel):
    """Request to initiate a single AI-powered call"""
    lead_id: str
    campaign_id: Optional[str] = None
    prompt_override: Optional[str] = None  # Override AI Config prompt
    voice: str = "nat"
    first_sentence: Optional[str] = None


@router.post("/initiate", status_code=status.HTTP_201_CREATED)
async def initiate_ai_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Initiate an AI-powered call using Bland AI + OpenAI GPT-4.1-mini    
    User can override prompt or use configured AI prompt from settings
    """
    
    # Get lead
    lead = db.query(Lead).filter(
        Lead.id == request.lead_id,
        Lead.tenant_id == tenant_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get campaign if specified
    campaign = None
    if request.campaign_id:
        campaign = db.query(Campaign).filter(
            Campaign.id == request.campaign_id,
            Campaign.tenant_id == tenant_id
        ).first()
    
    # Build AI prompt - Priority: 1. Override, 2. Campaign, 3. Default
    if request.prompt_override:
        ai_prompt = request.prompt_override
    else:
        # Use default smart prompt
        ai_prompt = f"""You are a professional and friendly sales representative.

Lead Information:
- Name: {lead.first_name} {lead.last_name}
- Company: {lead.company or 'Unknown'}
- Phone: {lead.phone}

Your Goal:
Have a natural conversation to understand their needs and qualify their interest.

Instructions:
1. Greet them warmly: "Hi {lead.first_name}, how are you today?"
2. Introduce yourself and company briefly
3. Ask about their current challenges or pain points
4. Listen actively - let them talk
5. If interested: Offer next steps (demo, meeting, information)
6. If not interested or busy: Thank them politely and offer email follow-up

Tone: Friendly, professional, consultative (never pushy or salesy)

Important Rules:
- Always respect their time
- If they say "not interested" or "busy", politely end the call
- Don't argue or pressure them
- Offer to send information via email as an alternative
- Keep the call under 5 minutes unless they're very engaged
"""
    
    # Prepare metadata
    metadata = {
        "lead_id": str(lead.id),
        "tenant_id": str(tenant_id),
        "lead_name": f"{lead.first_name} {lead.last_name}",
    }
    if campaign:
        metadata["campaign_id"] = str(campaign.id)
    
    try:
        # Initiate call via Bland AI with OpenAI GPT-4 model
        bland_response = await bland_client.initiate_call(
            phone_number=lead.phone,
            task=ai_prompt,
            voice=request.voice,
            model="enhanced",  # GPT-4 level intelligence
            first_sentence=request.first_sentence or f"Hi {lead.first_name}, how are you today?",
            wait_for_greeting=True,
            record=True,
            webhook=os.getenv("BLAND_WEBHOOK_URL"),
            metadata=metadata,
            max_duration=300,
            temperature=0.7
        )
        
        # Create call record
        call = Call(
            tenant_id=tenant_id,
            lead_id=lead.id,
            campaign_id=campaign.id if campaign else None,
            status=CallStatus.PENDING,
            external_call_id=bland_response.get("call_id"),
            created_at=datetime.utcnow()
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        
        return {
            "success": True,
            "call_id": str(call.id),
            "bland_call_id": bland_response.get("call_id"),
            "status": bland_response.get("status"),
            "message": f"AI call initiated to {lead.first_name} {lead.last_name}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call_data: CallCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create a call record (legacy endpoint - use /initiate for AI calls)"""
    
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


@router.post("/webhook/bland", include_in_schema=False)
async def bland_webhook_handler(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Webhook endpoint for Bland AI call events
    
    Events: call.started, call.completed, call.failed
    """
    
    event = payload.get("event")
    call_id = payload.get("call_id")
    
    if not call_id:
        return {"status": "ignored", "reason": "no call_id"}
    
    # Find call in database
    call = db.query(Call).filter(Call.external_call_id == call_id).first()
    
    if not call:
        return {"status": "ignored", "reason": "call not found"}
    
    # Handle events
    if event == "call.started":
        call.status = CallStatus.IN_PROGRESS
        call.started_at = datetime.utcnow()
        db.commit()
        
    elif event == "call.completed":
        # Process in background
        background_tasks.add_task(process_completed_call, call_id, db)
        
    elif event == "call.failed":
        call.status = CallStatus.FAILED
        call.ended_at = datetime.utcnow()
        call.notes = payload.get("error_message", "Call failed")
        db.commit()
    
    return {"status": "processed", "event": event}


async def process_completed_call(bland_call_id: str, db: Session):
    """Background task to fetch and process completed call details"""
    try:
        # Fetch full details from Bland AI
        call_details = await bland_client.get_call_details(bland_call_id)
        
        # Find call
        call = db.query(Call).filter(Call.external_call_id == bland_call_id).first()
        if not call:
            return
        
        # Extract data
        transcripts = call_details.get("transcripts", [])
        call_length = call_details.get("call_length", 0)
        answered_by = call_details.get("answered_by")
        recording_url = call_details.get("recording_url")
        
        # Analyze with AI
        outcome = bland_client.analyze_outcome(transcripts)
        sentiment = bland_client.analyze_sentiment(transcripts)
        
        # Calculate cost
        voice = call_details.get("request_data", {}).get("voice", "nat")
        cost = bland_client.calculate_cost(call_length, voice)
        
        # Map Bland AI outcomes to our enum
        outcome_map = {
            "interested": CallOutcome.INTERESTED,
            "not_interested": CallOutcome.NOT_INTERESTED,
            "callback": CallOutcome.CALLBACK,
            "voicemail": CallOutcome.VOICEMAIL,
            "no_answer": CallOutcome.NO_ANSWER,
        }
        
        # Update call record
        call.status = CallStatus.COMPLETED
        call.duration_seconds = call_length
        call.outcome = outcome_map.get(outcome, CallOutcome.NO_ANSWER)
        call.sentiment = sentiment
        call.transcript = transcripts  # Store as JSON
        call.recording_url = recording_url
        call.cost = cost
        call.ended_at = datetime.utcnow()
        
        # Add helpful notes
        if answered_by == "voicemail":
            call.notes = "Voicemail detected - message left"
        elif answered_by == "no-answer":
            call.notes = "No answer"
        elif outcome == "interested":
           call.notes = "Lead expressed interest ✅"
        elif outcome == "not_interested":
            call.notes = "Lead not interested"
        elif outcome == "callback":
            call.notes = "Lead requested callback"
        
        db.commit()
        
    except Exception as e:
        print(f"Error processing completed call {bland_call_id}: {e}")
