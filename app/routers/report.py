from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List, Annotated
from datetime import datetime, timedelta
import uuid
import os
from app.database import get_session
from app.models.user import User
from app.models.emergency_report import (
    EmergencyReport, 
    ReportStatus
)
from app.schemas.report import (
    ReportPublic,
    ReportSubmissionResponse,
    ReportListResponse,
    ReportStatusUpdateResponse,
    ReportSummary,
    FileUploadResponse,
    ReportLocation,
    ReportMapData,
    ReportStatusUpdate
)
from app.core.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/reports", tags=["reports"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/submit", response_model=ReportSubmissionResponse)
async def submit_emergency_report(
    latitude: Annotated[float, Form(ge=-90, le=90)],
    longitude: Annotated[float, Form(ge=-180, le=180)],
    description: Annotated[str, Form(max_length=1000)],
    category: Annotated[str, Form()] = "FLOOD",
    priority: Annotated[str, Form()] = "MEDIUM",
    contact_number: Annotated[Optional[str], Form()] = None,
    additional_notes: Annotated[Optional[str], Form()] = None,
    photo_evidence: Annotated[Optional[UploadFile], File()] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit an emergency report with optional photo evidence.
    Handles multipart/form-data for file uploads.
    Protected endpoint requiring JWT authentication.
    """
    # Priority is already set in the function parameter
    
    # Handle file upload if provided
    photo_url = None
    if photo_evidence and photo_evidence.filename:
        # Generate unique filename
        file_extension = os.path.splitext(photo_evidence.filename)[1]
        unique_filename = f"report_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Simulate file saving (in production, you'd save to cloud storage)
        try:
            # Read file content
            content = await photo_evidence.read()
            
            # Save file locally (simulation)
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Generate public URL (placeholder)
            photo_url = f"/files/report_{uuid.uuid4()}.jpg"
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    # Create emergency report
    db_report = EmergencyReport(
        user_id=current_user.id,
        latitude=latitude,
        longitude=longitude,
        description=description,
        photo_url=photo_url,
        status=ReportStatus.PENDING,
        priority=priority,
        category=category,
        contact_number=contact_number,
        additional_notes=additional_notes,
        updated_at=datetime.utcnow()
    )
    
    session.add(db_report)
    await session.commit()
    await session.refresh(db_report)
    
    # Create response
    report_public = ReportPublic(
        **db_report.model_dump(),
        submitter_username=current_user.username,
        time_since_submission="Just now"
    )
    
    return ReportSubmissionResponse(
        message="Emergency report submitted successfully",
        report_id=db_report.id,
        report=report_public
    )


@router.get("/my", response_model=ReportListResponse)
async def get_my_reports(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all emergency reports submitted by the current authenticated user.
    """
    result = await session.execute(
        select(EmergencyReport)
        .where(EmergencyReport.user_id == current_user.id)
        .order_by(desc(EmergencyReport.timestamp))
    )
    reports = result.scalars().all()
    
    # Transform to public format
    report_publics = []
    status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CANCELLED": 0}
    
    for report in reports:
        # Calculate time since submission
        time_diff = datetime.utcnow() - report.timestamp
        if time_diff.days > 0:
            time_since = f"{time_diff.days} day(s) ago"
        elif time_diff.seconds > 3600:
            time_since = f"{time_diff.seconds // 3600} hour(s) ago"
        elif time_diff.seconds > 60:
            time_since = f"{time_diff.seconds // 60} minute(s) ago"
        else:
            time_since = "Just now"
        
        report_public = ReportPublic(
            **report.model_dump(),
            submitter_username=current_user.username,
            time_since_submission=time_since
        )
        report_publics.append(report_public)
        status_counts[report.status.value] += 1
    
    return ReportListResponse(
        reports=report_publics,
        total_reports=len(reports),
        pending_reports=status_counts["PENDING"],
        in_progress_reports=status_counts["IN_PROGRESS"],
        resolved_reports=status_counts["RESOLVED"]
    )


@router.put("/{report_id}/status", response_model=ReportStatusUpdateResponse)
async def update_report_status(
    report_id: int,
    status_update: ReportStatusUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update the status of a specific emergency report.
    Admin only endpoint.
    """
    # Get the report
    result = await session.execute(
        select(EmergencyReport).where(EmergencyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency report not found"
        )
    
    # Store previous status
    previous_status = report.status
    
    # Update report
    report.status = status_update.status
    report.updated_at = datetime.utcnow()
    
    if status_update.resolution_notes:
        report.resolution_notes = status_update.resolution_notes
    
    if status_update.assigned_to:
        report.assigned_to = status_update.assigned_to
    
    await session.commit()
    await session.refresh(report)
    
    return ReportStatusUpdateResponse(
        message="Report status updated successfully",
        report_id=report.id,
        previous_status=previous_status,
        new_status=report.status,
        updated_at=report.updated_at
    )


@router.get("/all", response_model=ReportListResponse)
async def get_all_reports(
    status_filter: Optional[ReportStatus] = None,
    priority_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all emergency reports with optional filtering.
    Admin only endpoint.
    """
    query = select(EmergencyReport).order_by(desc(EmergencyReport.timestamp))
    
    if status_filter:
        query = query.where(EmergencyReport.status == status_filter)
    
    if priority_filter:
        query = query.where(EmergencyReport.priority == priority_filter)
    
    result = await session.execute(query)
    reports = result.scalars().all()
    
    # Transform to public format
    report_publics = []
    status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CANCELLED": 0}
    
    for report in reports:
        # Get submitter username
        user_result = await session.execute(
            select(User).where(User.id == report.user_id)
        )
        user = user_result.scalar_one_or_none()
        submitter_username = user.username if user else "Unknown"
        
        # Calculate time since submission
        time_diff = datetime.utcnow() - report.timestamp
        if time_diff.days > 0:
            time_since = f"{time_diff.days} day(s) ago"
        elif time_diff.seconds > 3600:
            time_since = f"{time_diff.seconds // 3600} hour(s) ago"
        elif time_diff.seconds > 60:
            time_since = f"{time_diff.seconds // 60} minute(s) ago"
        else:
            time_since = "Just now"
        
        report_public = ReportPublic(
            **report.model_dump(),
            submitter_username=submitter_username,
            time_since_submission=time_since
        )
        report_publics.append(report_public)
        status_counts[report.status.value] += 1
    
    return ReportListResponse(
        reports=report_publics,
        total_reports=len(reports),
        pending_reports=status_counts["PENDING"],
        in_progress_reports=status_counts["IN_PROGRESS"],
        resolved_reports=status_counts["RESOLVED"]
    )


@router.get("/summary", response_model=ReportSummary)
async def get_reports_summary(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get summary statistics for all reports.
    Admin only endpoint.
    """
    # Get status counts
    status_result = await session.execute(
        select(
            EmergencyReport.status,
            func.count(EmergencyReport.id).label('count')
        )
        .group_by(EmergencyReport.status)
    )
    status_counts = {row.status.value: row.count for row in status_result}
    
    # Get priority counts
    priority_result = await session.execute(
        select(
            EmergencyReport.priority,
            func.count(EmergencyReport.id).label('count')
        )
        .group_by(EmergencyReport.priority)
    )
    priority_counts = {row.priority: row.count for row in priority_result}
    
    # Get total count
    total_result = await session.execute(
        select(func.count(EmergencyReport.id))
    )
    total_reports = total_result.scalar() or 0
    
    return ReportSummary(
        total_reports=total_reports,
        pending_count=status_counts.get("PENDING", 0),
        in_progress_count=status_counts.get("IN_PROGRESS", 0),
        resolved_count=status_counts.get("RESOLVED", 0),
        cancelled_count=status_counts.get("CANCELLED", 0),
        critical_priority_count=priority_counts.get("CRITICAL", 0),
        high_priority_count=priority_counts.get("HIGH", 0),
        medium_priority_count=priority_counts.get("MEDIUM", 0),
        low_priority_count=priority_counts.get("LOW", 0)
    )


@router.get("/map-data", response_model=ReportMapData)
async def get_reports_map_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get report locations for map display.
    """
    # Get active reports (not resolved or cancelled)
    result = await session.execute(
        select(EmergencyReport)
        .where(EmergencyReport.status.in_([ReportStatus.PENDING, ReportStatus.IN_PROGRESS]))
        .order_by(desc(EmergencyReport.timestamp))
    )
    reports = result.scalars().all()
    
    report_locations = []
    for report in reports:
        report_location = ReportLocation(
            id=report.id,
            latitude=report.latitude,
            longitude=report.longitude,
            status=report.status,
            priority=report.priority,
            category=report.category,
            description=report.description,
            timestamp=report.timestamp,
            photo_url=report.photo_url
        )
        report_locations.append(report_location)
    
    return ReportMapData(
        reports=report_locations,
        total_active_reports=len(report_locations),
        last_updated=datetime.utcnow()
    )


@router.get("/{report_id}", response_model=ReportPublic)
async def get_report_details(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific report.
    Users can only view their own reports, admins can view all.
    """
    result = await session.execute(
        select(EmergencyReport).where(EmergencyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency report not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and report.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own reports"
        )
    
    # Get submitter username
    user_result = await session.execute(
        select(User).where(User.id == report.user_id)
    )
    user = user_result.scalar_one_or_none()
    submitter_username = user.username if user else "Unknown"
    
    # Calculate time since submission
    time_diff = datetime.utcnow() - report.timestamp
    if time_diff.days > 0:
        time_since = f"{time_diff.days} day(s) ago"
    elif time_diff.seconds > 3600:
        time_since = f"{time_diff.seconds // 3600} hour(s) ago"
    elif time_diff.seconds > 60:
        time_since = f"{time_diff.seconds // 60} minute(s) ago"
    else:
        time_since = "Just now"
    
    return ReportPublic(
        **report.model_dump(),
        submitter_username=submitter_username,
        time_since_submission=time_since
    )
