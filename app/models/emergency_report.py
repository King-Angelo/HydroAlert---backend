from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ReportSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReportCategory(str, Enum):
    FLOOD = "FLOOD"
    LANDSLIDE = "LANDSLIDE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    OTHER = "OTHER"

class ReportStatus(str, Enum):
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class EmergencyReport(SQLModel, table=True):
    __tablename__ = "emergencyreport"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    location_lat: float = Field(ge=-90, le=90)
    location_lng: float = Field(ge=-180, le=180)
    severity: ReportSeverity
    category: ReportCategory
    status: ReportStatus = ReportStatus.PENDING
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    triaged_at: Optional[datetime] = None
    triaged_by: Optional[int] = Field(foreign_key="user.id", default=None)
    triage_notes: Optional[str] = Field(default=None, max_length=1000)
    location_geom: Optional[str] = Field(sa_column=Column(String), description="Location geometry as text (PostGIS not available)")
    
    # Relationships
    attachments: List["ReportAttachment"] = Relationship(back_populates="report")
    # user: Optional["User"] = Relationship(back_populates="reports")  # Temporarily disabled due to foreign key ambiguity

class ReportAttachment(SQLModel, table=True):
    __tablename__ = "reportattachment"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(primary_key=True)
    report_id: int = Field(foreign_key="emergencyreport.id")
    original_filename: str = Field(max_length=255)
    stored_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int
    content_type: str = Field(max_length=100)
    file_hash: str = Field(max_length=64)  # SHA256 hash
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    is_processed: bool = False
    
    # Relationships
    report: Optional["EmergencyReport"] = Relationship(back_populates="attachments")

# Pydantic schemas for API
class EmergencyReportCreate(SQLModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    location_lat: float = Field(..., ge=-90, le=90)
    location_lng: float = Field(..., ge=-180, le=180)
    severity: ReportSeverity
    category: ReportCategory
    contact_phone: Optional[str] = Field(None, regex="^\\+?[1-9]\\d{1,14}$")

class ReportAttachmentResponse(SQLModel):
    id: int
    original_filename: str
    file_size: int
    content_type: str
    uploaded_at: datetime

class EmergencyReportResponse(SQLModel):
    id: int
    title: str
    description: str
    location_lat: float
    location_lng: float
    severity: ReportSeverity
    category: ReportCategory
    status: ReportStatus
    contact_phone: Optional[str]
    submitted_at: datetime
    attachments: List[ReportAttachmentResponse] = []
