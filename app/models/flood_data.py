from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FloodReadingBase(SQLModel):
    sensor_id: str = Field(max_length=50, description="Sensor identifier")
    water_level_cm: float = Field(ge=0, description="Water level in centimeters")
    rainfall_mm: float = Field(ge=0, description="Rainfall in millimeters")
    risk_level: RiskLevel = Field(description="Flood risk assessment level")
    location_lat: Optional[float] = Field(default=None, ge=-90, le=90, description="Latitude coordinate")
    location_lng: Optional[float] = Field(default=None, ge=-180, le=180, description="Longitude coordinate")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes")


class FloodReading(FloodReadingBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True, description="Reading timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    
    # Relationships can be added here if needed
    # sensor: Optional["Sensor"] = Relationship(back_populates="readings")


class FloodReadingCreate(FloodReadingBase):
    pass


class FloodReadingRead(FloodReadingBase):
    id: int
    timestamp: datetime
    created_at: datetime


class FloodReadingUpdate(SQLModel):
    sensor_id: Optional[str] = Field(default=None, max_length=50)
    water_level_cm: Optional[float] = Field(default=None, ge=0)
    rainfall_mm: Optional[float] = Field(default=None, ge=0)
    risk_level: Optional[RiskLevel] = None
    location_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    location_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    notes: Optional[str] = Field(default=None, max_length=500)


def calculate_risk_level(water_level_cm: float, rainfall_mm: float) -> RiskLevel:
    """
    Calculate flood risk level based on water level and rainfall
    """
    if water_level_cm >= 100 or rainfall_mm >= 50:
        return RiskLevel.CRITICAL
    elif water_level_cm >= 75 or rainfall_mm >= 30:
        return RiskLevel.HIGH
    elif water_level_cm >= 50 or rainfall_mm >= 20:
        return RiskLevel.MODERATE
    else:
        return RiskLevel.LOW
