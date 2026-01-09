"""Calls API routes with Bland AI + OpenAI Integration"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import json

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
    
    query = db.query(Call).filter(Call.tenant_id == str(tenant_id))
    
    if status_filter:
        query = query.filter(Call.status == status_filter)
    
    if outcome_filter:
        query = query.filter(Call.outcome == outcome_filter)
    
    if campaign_id:
        query = query.filter(Call.campaign_id == str(campaign_id))
    
    if lead_id:
        query = query.filter(Call.lead_id == str(lead_id))
    
    calls = query.order_by(Call.created_at.desc()).all()
    
    return [CallResponse.from_orm(call) for call in calls]


@router.get("/active", response_model=list[CallResponse])
async def get_active_calls(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get currently active calls"""
    
    calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
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
        Call.tenant_id == str(tenant_id),
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
        Call.tenant_id == str(tenant_id),
        Call.created_at >= start_date
    )
    
    total_calls = base_query.count()
    
    active_calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.status == CallStatus.IN_PROGRESS
    ).count()
    
    ringing = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.status == CallStatus.RINGING
    ).count()
    
    queued = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
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
        Call.id == str(call_id),
        Call.tenant_id == str(tenant_id)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return CallResponse.from_orm(call)


@router.post("/{call_id}/sync")
async def sync_call_from_bland(
    call_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Sync call details from Bland AI.
    Fetches transcript, outcome, sentiment, recording, etc.
    Use this after a call completes to get the full details.
    """
    
    call = db.query(Call).filter(
        Call.id == str(call_id),
        Call.tenant_id == str(tenant_id)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if not call.external_call_id:
        raise HTTPException(status_code=400, detail="No Bland AI call ID found for this call")
    
    try:
        # Fetch details from Bland AI
        call_details = await bland_client.get_call_details(call.external_call_id)
        
        # Extract data - Bland AI uses both 'transcripts' (list) and 'concatenated_transcript' (string)
        transcripts = call_details.get("transcripts", [])
        concatenated_transcript = call_details.get("concatenated_transcript", "")
        call_length = call_details.get("call_length", 0)  # In minutes
        answered_by = call_details.get("answered_by")
        recording_url = call_details.get("recording_url")
        call_status = call_details.get("status", "completed")
        price = call_details.get("price", 0)  # Bland AI returns price in cents
        
        # Use concatenated_transcript for analysis (easier to read)
        outcome = bland_client.analyze_outcome(transcripts)
        sentiment = bland_client.analyze_sentiment(transcripts)
        
        # Map outcomes
        outcome_map = {
            "interested": CallOutcome.INTERESTED,
            "not_interested": CallOutcome.NOT_INTERESTED,
            "callback": CallOutcome.CALLBACK,
            "voicemail": CallOutcome.VOICEMAIL,
            "no_answer": CallOutcome.NO_ANSWER,
        }
        
        # Update call record
        if call_status == "completed" or call_length > 0:
            call.status = CallStatus.COMPLETED
        
        # Convert call_length from minutes to seconds
        call.duration_seconds = int(call_length * 60) if call_length else 0
        call.outcome = outcome_map.get(outcome, CallOutcome.NO_ANSWER)
        call.sentiment = sentiment
        # Store concatenated transcript (easier to display) or JSON of transcripts array
        call.transcript = concatenated_transcript if concatenated_transcript else json.dumps(transcripts)
        call.recording_url = recording_url
        call.cost = int(price * 100) if price else 0  # Store as cents
        
        if not call.ended_at and call_length > 0:
            call.ended_at = datetime.utcnow()
        
        # Add notes
        if answered_by == "voicemail":
            call.notes = "Voicemail detected"
        elif answered_by == "no-answer":
            call.notes = "No answer"
        elif outcome == "interested":
            call.notes = "Lead expressed interest ✅"
        elif outcome == "not_interested":
            call.notes = "Lead not interested"
        elif outcome == "callback":
            call.notes = "Lead requested callback"
        
        db.commit()
        db.refresh(call)
        
        return {
            "success": True,
            "message": "Call synced successfully",
            "call_id": str(call.id),
            "outcome": outcome,
            "sentiment": sentiment,
            "duration_seconds": call_length,
            "transcript_lines": len(transcripts),
            "recording_url": recording_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync call: {str(e)}")


@router.post("/sync-all")
async def sync_all_pending_calls(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Sync all calls that have Bland AI IDs but no outcome.
    Useful for batch updating call results.
    """
    
    # Find calls with external IDs but no outcome
    pending_calls = db.query(Call).filter(
        Call.tenant_id == str(tenant_id),
        Call.external_call_id.isnot(None),
        Call.outcome == None
    ).all()
    
    synced = 0
    errors = 0
    
    for call in pending_calls:
        try:
            call_details = await bland_client.get_call_details(call.external_call_id)
            
            transcripts = call_details.get("transcripts", [])
            concatenated_transcript = call_details.get("concatenated_transcript", "")
            call_length = call_details.get("call_length", 0)  # In minutes
            recording_url = call_details.get("recording_url")
            
            if call_length > 0:  # Only update if call actually happened
                outcome = bland_client.analyze_outcome(transcripts)
                sentiment = bland_client.analyze_sentiment(transcripts)
                
                outcome_map = {
                    "interested": CallOutcome.INTERESTED,
                    "not_interested": CallOutcome.NOT_INTERESTED,
                    "callback": CallOutcome.CALLBACK,
                    "voicemail": CallOutcome.VOICEMAIL,
                    "no_answer": CallOutcome.NO_ANSWER,
                }
                
                call.status = CallStatus.COMPLETED
                call.duration_seconds = int(call_length * 60) if call_length else 0
                call.outcome = outcome_map.get(outcome, CallOutcome.NO_ANSWER)
                call.sentiment = sentiment
                call.transcript = concatenated_transcript if concatenated_transcript else json.dumps(transcripts)
                call.recording_url = recording_url
                call.ended_at = datetime.utcnow()
                
                synced += 1
        except Exception as e:
            print(f"Error syncing call {call.id}: {e}")
            errors += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Synced {synced} calls, {errors} errors",
        "synced": synced,
        "errors": errors,
        "total_pending": len(pending_calls)
    }


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
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get campaign if specified
    campaign = None
    if request.campaign_id:
        campaign = db.query(Campaign).filter(
            Campaign.id == request.campaign_id,
            Campaign.tenant_id == str(tenant_id)
        ).first()
    
    # Format phone number to E.164 format for Bland AI
    def format_phone_e164(phone: str) -> str:
        """Format phone to E.164 format (e.g., +12125551234 for US, +919624076783 for India)"""
        # Remove all non-numeric characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # If already starts with +, return as-is
        if cleaned.startswith('+'):
            return cleaned
        
        # If starts with 00 (international prefix), replace with +
        if cleaned.startswith('00'):
            return '+' + cleaned[2:]
        
        # Check if it looks like an Indian number (10 digits starting with 6, 7, 8, or 9)
        if len(cleaned) == 10 and cleaned[0] in '6789':
            return f"+91{cleaned}"
        
        # If it's 12 digits and starts with 91 (India with country code but no +)
        if len(cleaned) == 12 and cleaned.startswith('91'):
            return f"+{cleaned}"
        
        # If it's 10 digits starting with other digits, assume US
        if len(cleaned) == 10:
            return f"+1{cleaned}"
        
        # If it's 11 digits and starts with 1 (US with country code but no +)
        if len(cleaned) == 11 and cleaned.startswith('1'):
            return f"+{cleaned}"
        
        # For any other international numbers, assume they need a +
        if len(cleaned) > 10:
            return f"+{cleaned}"
        
        # Default: add + and hope for the best
        return f"+{cleaned}"
    
    formatted_phone = format_phone_e164(lead.phone)
    
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
        # Get webhook URL from settings
        from app.config import settings
        webhook_url = settings.BLAND_WEBHOOK_URL if settings.BLAND_WEBHOOK_URL else None
        
        # Log the call attempt for debugging
        print(f"[BLAND AI] Initiating call to: {formatted_phone}")
        print(f"[BLAND AI] Original phone: {lead.phone}")
        print(f"[BLAND AI] Voice: {request.voice}")
        
        # Initiate call via Bland AI
        bland_response = await bland_client.initiate_call(
            phone_number=formatted_phone,  # Use formatted phone number
            task=ai_prompt,
            voice=request.voice,
            first_sentence=request.first_sentence or f"Hi {lead.first_name}, how are you today?",
            wait_for_greeting=True,
            record=True,
            webhook=webhook_url,
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
        Lead.tenant_id == str(tenant_id)
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
        Call.id == str(call_id),
        Call.tenant_id == str(tenant_id)
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
    call = db.query(Call).filter(Call.external_call_id == str(call_id)).first()
    
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
        
        # AUTO-UPDATE LEAD STATUS based on call outcome
        if call.lead_id:
            from app.models.enums import LeadStatus
            lead = db.query(Lead).filter(Lead.id == call.lead_id).first()
            if lead:
                if outcome == "interested":
                    lead.status = LeadStatus.INTERESTED
                    lead.notes = (lead.notes or "") + f"\n[Auto] Expressed interest on call {datetime.utcnow().strftime('%Y-%m-%d')}"
                elif outcome == "not_interested":
                    lead.status = LeadStatus.NOT_INTERESTED
                    lead.notes = (lead.notes or "") + f"\n[Auto] Not interested on call {datetime.utcnow().strftime('%Y-%m-%d')}"
                elif outcome == "callback":
                    lead.status = LeadStatus.CALLBACK
                    lead.notes = (lead.notes or "") + f"\n[Auto] Requested callback on {datetime.utcnow().strftime('%Y-%m-%d')}"
                elif answered_by in ["no-answer", "voicemail"]:
                    # Don't change status for voicemail/no answer, just log
                    lead.notes = (lead.notes or "") + f"\n[Auto] {answered_by} on {datetime.utcnow().strftime('%Y-%m-%d')}"
                else:
                    # Mark as contacted even if outcome is inconclusive
                    if lead.status == LeadStatus.NEW:
                        lead.status = LeadStatus.CONTACTED
        
        db.commit()
        
    except Exception as e:
        print(f"Error processing completed call {bland_call_id}: {e}")

