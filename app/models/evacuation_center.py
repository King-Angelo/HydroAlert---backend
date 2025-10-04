from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String
from typing import Optional
from datetime import datetime

class EvacuationCenter(SQLModel, table=True):
    __tablename__ = "evacuationcenter"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=255)
    location_lat: float = Field(ge=-90, le=90)
    location_lng: float = Field(ge=-180, le=180)
    location_geom: Optional[str] = Field(sa_column=Column(String), description="Location geometry as text (PostGIS not available)")
    capacity: int = Field(default=100, ge=1)
    current_occupancy: int = Field(default=0, ge=0)
    contact_info: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EvacuationCenterCreate(SQLModel):
    name: str = Field(..., min_length=3, max_length=255)
    location_lat: float = Field(..., ge=-90, le=90)
    location_lng: float = Field(..., ge=-180, le=180)
    capacity: int = Field(..., ge=1)
    contact_info: Optional[str] = Field(None, max_length=500)

class EvacuationCenterResponse(SQLModel):
    id: int
    name: str
    location_lat: float
    location_lng: float
    capacity: int
    current_occupancy: int
    contact_info: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class EvacuationCenterWithDistance(EvacuationCenterResponse):
    distance_m: float = Field(description="Distance in meters from query point")
