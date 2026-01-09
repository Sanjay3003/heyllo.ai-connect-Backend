"""Leads API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from typing import Optional
import csv
import io

from app.database import get_db
from app.models import Lead, Call
from app.models.enums import LeadStatus
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadListResponse
from app.schemas.call import CallResponse
from app.dependencies import get_current_user, get_current_tenant_id, get_pagination_params
from app.models import User

router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.get("", response_model=LeadListResponse)
async def get_leads(
    status_filter: Optional[LeadStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get all leads for the tenant"""
    
    # Base query
    query = db.query(Lead).filter(Lead.tenant_id == str(tenant_id))
    
    # Apply filters
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Lead.first_name.ilike(search_pattern),
                Lead.last_name.ilike(search_pattern),
                Lead.email.ilike(search_pattern),
                Lead.phone.ilike(search_pattern),
                Lead.company.ilike(search_pattern),
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    pagination = get_pagination_params(page, limit)
    leads = query.offset(pagination["skip"]).limit(pagination["limit"]).all()
    
    return LeadListResponse(
        total=total,
        page=page,
        page_size=limit,
        leads=[LeadResponse.from_orm(lead) for lead in leads]
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get a single lead"""
    
    lead = db.query(Lead).filter(
        Lead.id == str(lead_id),
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return LeadResponse.from_orm(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create a new lead"""
    
    new_lead = Lead(
        **lead_data.model_dump(),
        tenant_id=tenant_id
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    return LeadResponse.from_orm(new_lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update a lead"""
    
    lead = db.query(Lead).filter(
        Lead.id == str(lead_id),
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update fields
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.from_orm(lead)


@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def update_lead_status(
    lead_id: UUID,
    new_status: LeadStatus,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update lead status only"""
    
    lead = db.query(Lead).filter(
        Lead.id == str(lead_id),
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.status = new_status
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.from_orm(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Delete a lead"""
    
    lead = db.query(Lead).filter(
        Lead.id == str(lead_id),
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    db.delete(lead)
    db.commit()
    
    return None


@router.get("/{lead_id}/calls", response_model=list[CallResponse])
async def get_lead_calls(
    lead_id: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get call history for a lead"""
    
    # Verify lead exists and belongs to tenant
    lead = db.query(Lead).filter(
        Lead.id == str(lead_id),
        Lead.tenant_id == str(tenant_id)
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    calls = db.query(Call).filter(Call.lead_id == str(lead_id)).order_by(Call.created_at.desc()).all()
    
    return [CallResponse.from_orm(call) for call in calls]


@router.post("/import/csv")
async def import_leads_csv(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Import leads from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read CSV content
    content = await file.read()
    csv_text = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    
    imported_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # Phone is required
            if not row.get('phone'):
                errors.append(f"Row {row_num}: Phone number required")
                continue
            
            lead = Lead(
                tenant_id=tenant_id,
                first_name=row.get('first_name'),
                last_name=row.get('last_name'),
                email=row.get('email'),
                phone=row.get('phone'),
                company=row.get('company'),
                status=LeadStatus.NEW
            )
            db.add(lead)
            imported_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    db.commit()
    
    return {
        "imported": imported_count,
        "errors": errors
    }


@router.get("/export/csv")
async def export_leads_csv(
    status_filter: Optional[LeadStatus] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Export leads to CSV"""
    
    # Query leads
    query = db.query(Lead).filter(Lead.tenant_id == str(tenant_id))
    
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    
    leads = query.all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['first_name', 'last_name', 'email', 'phone', 'company', 'status'])
    
    # Write data
    for lead in leads:
        writer.writerow([
            lead.first_name or '',
            lead.last_name or '',
            lead.email or '',
            lead.phone,
            lead.company or '',
            lead.status.value
        ])
    
    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )
