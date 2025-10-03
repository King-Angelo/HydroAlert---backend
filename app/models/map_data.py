from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum


class CenterStatus(str, Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    MAINTENANCE = "MAINTENANCE"


class EvacuationCenterBase(SQLModel):
    name: str = Field(max_length=100, description="Name of the evacuation center")
    latitude: float = Field(ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(ge=-180, le=180, description="Longitude coordinate")
    max_capacity: int = Field(gt=0, description="Maximum capacity of the center")
    current_occupancy: int = Field(default=0, ge=0, description="Current number of occupants")
    status: CenterStatus = Field(default=CenterStatus.OPEN, description="Current status of the center")
    address: str = Field(max_length=200, description="Physical address of the center")
    contact_number: Optional[str] = Field(default=None, max_length=20, description="Contact number")
    facilities: Optional[str] = Field(default=None, max_length=500, description="Available facilities")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes")


class EvacuationCenter(EvacuationCenterBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships can be added here if needed
    # evacuations: List["Evacuation"] = Relationship(back_populates="center")


class EvacuationCenterCreate(EvacuationCenterBase):
    pass


class EvacuationCenterRead(EvacuationCenterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    occupancy_percentage: float  # Calculated field


class EvacuationCenterUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    max_capacity: Optional[int] = Field(default=None, gt=0)
    current_occupancy: Optional[int] = Field(default=None, ge=0)
    status: Optional[CenterStatus] = None
    address: Optional[str] = Field(default=None, max_length=200)
    contact_number: Optional[str] = Field(default=None, max_length=20)
    facilities: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)


class OccupancyUpdate(SQLModel):
    current_occupancy: int = Field(ge=0, description="New occupancy count")
    status: Optional[CenterStatus] = Field(default=None, description="Optional status update")


def calculate_occupancy_percentage(current_occupancy: int, max_capacity: int) -> float:
    """Calculate occupancy percentage"""
    if max_capacity == 0:
        return 0.0
    return round((current_occupancy / max_capacity) * 100, 2)


def determine_center_status(current_occupancy: int, max_capacity: int, current_status: CenterStatus) -> CenterStatus:
    """
    Automatically determine center status based on occupancy
    """
    occupancy_percentage = calculate_occupancy_percentage(current_occupancy, max_capacity)
    
    if current_status == CenterStatus.CLOSED or current_status == CenterStatus.MAINTENANCE:
        return current_status  # Don't auto-change these statuses
    
    if occupancy_percentage >= 100:
        return CenterStatus.FULL
    elif occupancy_percentage >= 90:
        return CenterStatus.CLOSING
    else:
        return CenterStatus.OPEN
