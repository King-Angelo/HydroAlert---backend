from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.report_data import ReportStatus, EmergencyReportRead, EmergencyReportCreate, EmergencyReportUpdate, ReportStatusUpdate


class ReportPublic(EmergencyReportRead):
    """Public schema for returning report data to users/admins"""
    submitter_username: Optional[str] = None
    time_since_submission: Optional[str] = None  # Human-readable time difference


class ReportSubmissionResponse(BaseModel):
    """Response schema for report submission"""
    message: str
    report_id: int
    report: ReportPublic


class ReportListResponse(BaseModel):
    """Response schema for list of reports"""
    reports: List[ReportPublic]
    total_reports: int
    pending_reports: int
    in_progress_reports: int
    resolved_reports: int


class ReportStatusUpdateResponse(BaseModel):
    """Response schema for status updates"""
    message: str
    report_id: int
    previous_status: ReportStatus
    new_status: ReportStatus
    updated_at: datetime


class ReportSummary(BaseModel):
    """Summary statistics for reports"""
    total_reports: int
    pending_count: int
    in_progress_count: int
    resolved_count: int
    cancelled_count: int
    critical_priority_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int


class ReportFormData(BaseModel):
    """Schema for form data submission"""
    latitude: float = Field(ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(ge=-180, le=180, description="Longitude coordinate")
    description: str = Field(max_length=1000, description="Report description")
    category: str = Field(default="FLOOD", description="Report category")
    priority: str = Field(default="MEDIUM", description="Priority level")
    contact_number: Optional[str] = Field(default=None, max_length=20, description="Contact number")
    additional_notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes")


class FileUploadResponse(BaseModel):
    """Response schema for file upload"""
    filename: str
    file_url: str
    file_size: int
    content_type: str
    upload_timestamp: datetime


class ReportAnalytics(BaseModel):
    """Analytics data for reports"""
    reports_by_status: dict
    reports_by_priority: dict
    reports_by_category: dict
    reports_by_hour: dict
    average_resolution_time: Optional[float] = None
    total_reports_today: int
    total_reports_this_week: int
    total_reports_this_month: int


class ReportLocation(BaseModel):
    """Location data for map display"""
    id: int
    latitude: float
    longitude: float
    status: ReportStatus
    priority: str
    category: str
    description: str
    timestamp: datetime
    photo_url: Optional[str] = None


class ReportMapData(BaseModel):
    """Map data response for reports"""
    reports: List[ReportLocation]
    total_active_reports: int
    last_updated: datetime


# Re-export the core schemas for convenience
__all__ = [
    "ReportPublic",
    "ReportSubmissionResponse",
    "ReportListResponse", 
    "ReportStatusUpdateResponse",
    "ReportSummary",
    "ReportFormData",
    "FileUploadResponse",
    "ReportAnalytics",
    "ReportLocation",
    "ReportMapData",
    "EmergencyReportCreate",
    "EmergencyReportUpdate",
    "EmergencyReportRead",
    "ReportStatusUpdate",
    "ReportStatus"
]
