from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SensorStatus(str, Enum):
    """Sensor operational status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"
    LOW_BATTERY = "LOW_BATTERY"
    LOW_SIGNAL = "LOW_SIGNAL"

class SensorType(str, Enum):
    """Types of sensors"""
    WATER_LEVEL = "WATER_LEVEL"
    RAINFALL = "RAINFALL"
    COMBINED = "COMBINED"
    WEATHER = "WEATHER"

class Sensor(SQLModel, table=True):
    """Sensor device metadata and configuration"""
    __tablename__ = "sensor"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(primary_key=True)
    sensor_id: str = Field(unique=True, max_length=50, index=True, description="Unique sensor identifier")
    name: str = Field(max_length=100, description="Human-readable sensor name")
    description: Optional[str] = Field(default=None, max_length=500, description="Sensor description")
    sensor_type: SensorType = Field(default=SensorType.COMBINED, description="Type of sensor")
    
    # Location information
    location_lat: float = Field(ge=-90, le=90, description="Latitude coordinate")
    location_lng: float = Field(ge=-180, le=180, description="Longitude coordinate")
    location_geom: Optional[str] = Field(sa_column=Column(String), description="Location geometry as text (PostGIS not available)")
    location_description: Optional[str] = Field(default=None, max_length=200, description="Human-readable location")
    
    # Device health and status
    battery_level: Optional[int] = Field(default=None, ge=0, le=100, description="Battery level percentage")
    signal_strength: Optional[int] = Field(default=None, ge=0, le=100, description="Signal strength percentage")
    status: SensorStatus = Field(default=SensorStatus.ACTIVE, description="Current sensor status")
    is_active: bool = Field(default=True, description="Whether sensor is active")
    
    # Maintenance and lifecycle
    installation_date: datetime = Field(default_factory=datetime.utcnow, description="When sensor was installed")
    last_maintenance: Optional[datetime] = Field(default=None, description="Last maintenance date")
    last_reading_time: Optional[datetime] = Field(default=None, description="Last time sensor sent data")
    next_maintenance_due: Optional[datetime] = Field(default=None, description="Next scheduled maintenance")
    
    # Configuration
    reading_interval_minutes: int = Field(default=15, ge=1, le=1440, description="Reading interval in minutes")
    battery_low_threshold: int = Field(default=20, ge=0, le=100, description="Battery low warning threshold")
    signal_low_threshold: int = Field(default=30, ge=0, le=100, description="Signal low warning threshold")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    health_logs: List["SensorHealth"] = Relationship(back_populates="sensor")
    readings: List["FloodReading"] = Relationship(back_populates="sensor")

class SensorHealth(SQLModel, table=True):
    """Time-series sensor health logging"""
    __tablename__ = "sensorhealth"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(primary_key=True)
    sensor_id: str = Field(foreign_key="sensor.sensor_id", index=True, description="Reference to sensor")
    battery_level: Optional[int] = Field(ge=0, le=100, description="Battery level at time of recording")
    signal_strength: Optional[int] = Field(ge=0, le=100, description="Signal strength at time of recording")
    status: SensorStatus = Field(description="Sensor status at time of recording")
    temperature_celsius: Optional[float] = Field(default=None, description="Device temperature if available")
    humidity_percent: Optional[float] = Field(default=None, ge=0, le=100, description="Ambient humidity if available")
    recorded_at: datetime = Field(default_factory=datetime.utcnow, index=True, description="When health data was recorded")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional health notes")
    
    # Relationships
    sensor: Optional["Sensor"] = Relationship(back_populates="health_logs")

# Pydantic schemas for API
class SensorCreate(SQLModel):
    """Schema for creating a new sensor"""
    sensor_id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sensor_type: SensorType = Field(default=SensorType.COMBINED)
    location_lat: float = Field(..., ge=-90, le=90)
    location_lng: float = Field(..., ge=-180, le=180)
    location_description: Optional[str] = Field(None, max_length=200)
    reading_interval_minutes: int = Field(default=15, ge=1, le=1440)
    battery_low_threshold: int = Field(default=20, ge=0, le=100)
    signal_low_threshold: int = Field(default=30, ge=0, le=100)

class SensorUpdate(SQLModel):
    """Schema for updating sensor information"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sensor_type: Optional[SensorType] = None
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)
    location_description: Optional[str] = Field(None, max_length=200)
    status: Optional[SensorStatus] = None
    is_active: Optional[bool] = None
    reading_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    battery_low_threshold: Optional[int] = Field(None, ge=0, le=100)
    signal_low_threshold: Optional[int] = Field(None, ge=0, le=100)
    next_maintenance_due: Optional[datetime] = None

class SensorResponse(SQLModel):
    """Schema for sensor API responses"""
    id: int
    sensor_id: str
    name: str
    description: Optional[str]
    sensor_type: SensorType
    location_lat: float
    location_lng: float
    location_description: Optional[str]
    battery_level: Optional[int]
    signal_strength: Optional[int]
    status: SensorStatus
    is_active: bool
    installation_date: datetime
    last_maintenance: Optional[datetime]
    last_reading_time: Optional[datetime]
    next_maintenance_due: Optional[datetime]
    reading_interval_minutes: int
    battery_low_threshold: int
    signal_low_threshold: int
    created_at: datetime
    updated_at: datetime

class SensorHealthCreate(SQLModel):
    """Schema for creating sensor health logs"""
    sensor_id: str = Field(..., min_length=3, max_length=50)
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    signal_strength: Optional[int] = Field(None, ge=0, le=100)
    status: SensorStatus
    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=500)

class SensorHealthResponse(SQLModel):
    """Schema for sensor health API responses"""
    id: int
    sensor_id: str
    battery_level: Optional[int]
    signal_strength: Optional[int]
    status: SensorStatus
    temperature_celsius: Optional[float]
    humidity_percent: Optional[float]
    recorded_at: datetime
    notes: Optional[str]

class SensorIngestData(SQLModel):
    """Schema for IoT sensor data ingestion"""
    sensor_id: str = Field(..., min_length=3, max_length=50)
    water_level_cm: float = Field(..., ge=0, description="Water level in centimeters")
    rainfall_mm: float = Field(..., ge=0, description="Rainfall in millimeters")
    location_lat: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    location_lng: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    battery_level: Optional[int] = Field(None, ge=0, le=100, description="Current battery level")
    signal_strength: Optional[int] = Field(None, ge=0, le=100, description="Current signal strength")
    temperature_celsius: Optional[float] = Field(None, description="Device temperature")
    humidity_percent: Optional[float] = Field(None, ge=0, le=100, description="Ambient humidity")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Reading timestamp")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")

class SensorSummary(SQLModel):
    """Summary statistics for sensor dashboard"""
    total_sensors: int
    active_sensors: int
    offline_sensors: int
    maintenance_due: int
    low_battery_count: int
    low_signal_count: int
    last_updated: datetime