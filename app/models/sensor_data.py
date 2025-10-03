from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from app.models.user import User


class SensorDataBase(SQLModel):
    water_level_cm: float = Field(ge=0, description="Water level in centimeters")
    rainfall_mm: float = Field(ge=0, description="Rainfall in millimeters")
    location_lat: Optional[float] = Field(default=None, ge=-90, le=90, description="Latitude")
    location_lng: Optional[float] = Field(default=None, ge=-180, le=180, description="Longitude")
    sensor_id: Optional[str] = Field(default=None, max_length=50, description="Sensor identifier")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes")


class SensorData(SensorDataBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="sensor_data")


class SensorDataCreate(SensorDataBase):
    pass


class SensorDataRead(SensorDataBase):
    id: int
    user_id: Optional[int]
    created_at: datetime


class SensorDataUpdate(SQLModel):
    water_level_cm: Optional[float] = Field(default=None, ge=0)
    rainfall_mm: Optional[float] = Field(default=None, ge=0)
    location_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    location_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    sensor_id: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
