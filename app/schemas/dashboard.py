from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.flood_data import RiskLevel, FloodReadingRead


class DashboardStatusResponse(BaseModel):
    """Response schema for dashboard status endpoint"""
    overall_status: str
    risk_level: RiskLevel
    latest_reading: Optional[FloodReadingRead]
    last_updated: Optional[datetime]
    alert_active: bool
    message: Optional[str] = None


class FloodStatusSummary(BaseModel):
    """Summary of flood status for dashboard display"""
    current_risk: RiskLevel
    water_level_cm: float
    rainfall_mm: float
    sensor_id: str
    location: Optional[dict] = None
    timestamp: datetime
    status_message: str


class DashboardMetrics(BaseModel):
    """Dashboard metrics and statistics"""
    total_readings: int
    average_water_level: float
    average_rainfall: float
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    last_24h_readings: int


class AlertStatus(BaseModel):
    """Alert status information"""
    is_active: bool
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# Re-export the flood reading schemas for convenience
from app.models.flood_data import FloodReadingCreate, FloodReadingUpdate

__all__ = [
    "DashboardStatusResponse",
    "FloodStatusSummary", 
    "DashboardMetrics",
    "AlertStatus",
    "FloodReadingCreate",
    "FloodReadingUpdate",
    "FloodReadingRead"
]
