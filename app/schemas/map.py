from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.map_data import CenterStatus, EvacuationCenterRead, EvacuationCenterCreate, EvacuationCenterUpdate, OccupancyUpdate


class EvacuationCenterResponse(EvacuationCenterRead):
    """Response schema for evacuation center data"""
    available_capacity: int
    is_available: bool


class EvacuationCenterListResponse(BaseModel):
    """Response schema for list of evacuation centers"""
    centers: List[EvacuationCenterResponse]
    total_centers: int
    open_centers: int
    full_centers: int
    total_capacity: int
    total_occupancy: int


class EvacuationCenterCreateResponse(BaseModel):
    """Response schema for center creation"""
    message: str
    center_id: int
    center: EvacuationCenterResponse


class OccupancyUpdateResponse(BaseModel):
    """Response schema for occupancy update"""
    message: str
    center_id: int
    previous_occupancy: int
    new_occupancy: int
    occupancy_percentage: float
    status: CenterStatus
    available_capacity: int


class CenterLocation(BaseModel):
    """Simple location schema for map display"""
    id: int
    name: str
    latitude: float
    longitude: float
    status: CenterStatus
    occupancy_percentage: float
    available_capacity: int


class MapDataResponse(BaseModel):
    """Response schema for map data including centers and flood status"""
    centers: List[CenterLocation]
    flood_zones: Optional[List[dict]] = None  # For future flood zone data
    last_updated: datetime


class CenterCapacityInfo(BaseModel):
    """Capacity information for a center"""
    center_id: int
    name: str
    max_capacity: int
    current_occupancy: int
    available_capacity: int
    occupancy_percentage: float
    status: CenterStatus


class CapacitySummaryResponse(BaseModel):
    """Summary of all center capacities"""
    centers: List[CenterCapacityInfo]
    total_capacity: int
    total_occupancy: int
    total_available: int
    overall_occupancy_percentage: float


# Re-export the core schemas for convenience
__all__ = [
    "EvacuationCenterResponse",
    "EvacuationCenterListResponse", 
    "EvacuationCenterCreateResponse",
    "OccupancyUpdateResponse",
    "CenterLocation",
    "MapDataResponse",
    "CenterCapacityInfo",
    "CapacitySummaryResponse",
    "EvacuationCenterCreate",
    "EvacuationCenterUpdate", 
    "EvacuationCenterRead",
    "OccupancyUpdate",
    "CenterStatus"
]
