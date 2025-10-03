from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum


class ReportStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class EmergencyReportBase(SQLModel):
    latitude: float = Field(ge=-90, le=90, description="Latitude coordinate of the incident")
    longitude: float = Field(ge=-180, le=180, description="Longitude coordinate of the incident")
    description: str = Field(max_length=1000, description="Detailed description of the emergency")
    photo_url: Optional[str] = Field(default=None, max_length=500, description="URL of uploaded photo evidence")
    status: ReportStatus = Field(default=ReportStatus.PENDING, description="Current status of the report")
    priority: str = Field(default="MEDIUM", description="Priority level: LOW, MEDIUM, HIGH, CRITICAL")
    category: str = Field(default="FLOOD", description="Report category: FLOOD, FIRE, MEDICAL, OTHER")
    contact_number: Optional[str] = Field(default=None, max_length=20, description="Contact number for follow-up")
    additional_notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes or information")


class EmergencyReport(EmergencyReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", description="ID of the user who submitted the report")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True, description="Report submission timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    assigned_to: Optional[str] = Field(default=None, max_length=100, description="Admin/responder assigned to this report")
    resolution_notes: Optional[str] = Field(default=None, max_length=1000, description="Notes about how the report was resolved")
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="reports")


class EmergencyReportCreate(EmergencyReportBase):
    pass


class EmergencyReportRead(EmergencyReportBase):
    id: int
    user_id: int
    timestamp: datetime
    updated_at: Optional[datetime]
    assigned_to: Optional[str]
    resolution_notes: Optional[str]


class EmergencyReportUpdate(SQLModel):
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    description: Optional[str] = Field(default=None, max_length=1000)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    status: Optional[ReportStatus] = None
    priority: Optional[str] = Field(default=None, description="Priority level: LOW, MEDIUM, HIGH, CRITICAL")
    category: Optional[str] = Field(default=None, description="Report category: FLOOD, FIRE, MEDICAL, OTHER")
    contact_number: Optional[str] = Field(default=None, max_length=20)
    additional_notes: Optional[str] = Field(default=None, max_length=500)
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)


class ReportStatusUpdate(SQLModel):
    status: ReportStatus
    resolution_notes: Optional[str] = Field(default=None, max_length=1000, description="Notes about resolution")
    assigned_to: Optional[str] = Field(default=None, max_length=100, description="Admin/responder assigned")


def determine_priority(description: str, category: str) -> str:
    """
    Automatically determine priority based on description keywords and category
    """
    description_lower = description.lower()
    
    # Critical keywords
    critical_keywords = ["emergency", "urgent", "trapped", "stuck", "help", "rescue", "danger"]
    if any(keyword in description_lower for keyword in critical_keywords):
        return "CRITICAL"
    
    # High priority keywords
    high_keywords = ["flooding", "water", "rising", "evacuate", "damage", "injury"]
    if any(keyword in description_lower for keyword in high_keywords):
        return "HIGH"
    
    # Category-based priority
    if category in ["MEDICAL", "FIRE"]:
        return "HIGH"
    elif category == "FLOOD":
        return "MEDIUM"
    else:
        return "LOW"
