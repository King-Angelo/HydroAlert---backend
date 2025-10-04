from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.user import User
from app.models.emergency_report import (
    EmergencyReportCreate, 
    EmergencyReportResponse, 
    ReportAttachmentResponse,
    ReportSeverity,
    ReportCategory
)
from app.services.report_service import ReportService
from app.core.file_validation import FileValidator

router = APIRouter(prefix="/api/mobile/reports", tags=["mobile-reports"])

@router.post("/submit", response_model=EmergencyReportResponse)
async def submit_emergency_report(
    title: str = Form(..., min_length=5, max_length=200),
    description: str = Form(..., min_length=10, max_length=2000),
    location_lat: float = Form(..., ge=-90, le=90),
    location_lng: float = Form(..., ge=-180, le=180),
    severity: str = Form(...),
    category: str = Form(...),
    contact_phone: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit emergency report with file attachments
    """
    # Validate severity and category
    try:
        severity_enum = ReportSeverity(severity.upper())
        category_enum = ReportCategory(category.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid severity or category value"
        )
    
    # Validate file count
    FileValidator.validate_file_count(len(files))
    
    # Validate coordinates
    if location_lat == 0 and location_lng == 0:
        raise HTTPException(
            status_code=400,
            detail="Coordinates cannot be zero"
        )
    
    # Create report data
    report_data = EmergencyReportCreate(
        title=title,
        description=description,
        location_lat=location_lat,
        location_lng=location_lng,
        severity=severity_enum,
        category=category_enum,
        contact_phone=contact_phone
    )
    
    report_service = ReportService()
    
    try:
        # Create report
        report = await report_service.create_report(report_data, current_user.id, session, current_user)
        
        # Process file uploads
        attachments = []
        for file in files:
            if file.filename:  # Only process files with names
                attachment = await report_service.process_file_upload(file, report.id, session)
                attachments.append(ReportAttachmentResponse(
                    id=attachment.id,
                    original_filename=attachment.original_filename,
                    file_size=attachment.file_size,
                    content_type=attachment.content_type,
                    uploaded_at=attachment.uploaded_at
                ))
        
        return EmergencyReportResponse(
            id=report.id,
            title=report.title,
            description=report.description,
            location_lat=report.location_lat,
            location_lng=report.location_lng,
            severity=report.severity,
            category=report.category,
            status=report.status,
            contact_phone=report.contact_phone,
            submitted_at=report.submitted_at,
            attachments=attachments
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=dict)
async def upload_evidence_files(
    report_id: int = Form(...),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload additional evidence files to existing report
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate file count
    FileValidator.validate_file_count(len(files))
    
    report_service = ReportService()
    
    # Verify report ownership
    report = await report_service.get_report_by_id(report_id, session)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if report.status != "PENDING":
        raise HTTPException(
            status_code=400, 
            detail="Cannot upload files to processed report"
        )
    
    # Process uploads
    uploaded_files = []
    for file in files:
        if file.filename:  # Only process files with names
            try:
                attachment = await report_service.process_file_upload(file, report_id, session)
                uploaded_files.append({
                    "id": attachment.id,
                    "filename": attachment.original_filename,
                    "file_size": attachment.file_size,
                    "uploaded_at": attachment.uploaded_at
                })
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error uploading {file.filename}: {str(e)}")
    
    return {
        "message": f"Successfully uploaded {len(uploaded_files)} files",
        "files": uploaded_files
    }

@router.get("/my-reports", response_model=List[EmergencyReportResponse])
async def get_my_reports(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current user's submitted reports
    """
    report_service = ReportService()
    reports = await report_service.get_user_reports(current_user.id, session)
    
    response_reports = []
    for report in reports:
        attachments = [
            ReportAttachmentResponse(
                id=att.id,
                original_filename=att.original_filename,
                file_size=att.file_size,
                content_type=att.content_type,
                uploaded_at=att.uploaded_at
            ) for att in report.attachments
        ]
        
        response_reports.append(EmergencyReportResponse(
            id=report.id,
            title=report.title,
            description=report.description,
            location_lat=report.location_lat,
            location_lng=report.location_lng,
            severity=report.severity,
            category=report.category,
            status=report.status,
            contact_phone=report.contact_phone,
            submitted_at=report.submitted_at,
            attachments=attachments
        ))
    
    return response_reports

@router.get("/{report_id}", response_model=EmergencyReportResponse)
async def get_report_details(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific report
    """
    report_service = ReportService()
    report = await report_service.get_report_by_id(report_id, session)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    attachments = [
        ReportAttachmentResponse(
            id=att.id,
            original_filename=att.original_filename,
            file_size=att.file_size,
            content_type=att.content_type,
            uploaded_at=att.uploaded_at
        ) for att in report.attachments
    ]
    
    return EmergencyReportResponse(
        id=report.id,
        title=report.title,
        description=report.description,
        location_lat=report.location_lat,
        location_lng=report.location_lng,
        severity=report.severity,
        category=report.category,
        status=report.status,
        contact_phone=report.contact_phone,
        submitted_at=report.submitted_at,
        attachments=attachments
    )
