from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MapBounds(BaseModel):
    """Map viewport bounds for filtering data"""
    north: float = Field(..., ge=-90, le=90, description="Northern boundary latitude")
    south: float = Field(..., ge=-90, le=90, description="Southern boundary latitude")
    east: float = Field(..., ge=-180, le=180, description="Eastern boundary longitude")
    west: float = Field(..., ge=-180, le=180, description="Western boundary longitude")
    
    def to_postgis_bounds(self) -> Dict[str, float]:
        """Convert to PostGIS-compatible bounds"""
        return {
            "min_lat": self.south,
            "max_lat": self.north,
            "min_lng": self.west,
            "max_lng": self.east
        }

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry"""
    type: str = Field(default="Point")
    coordinates: List[float] = Field(..., min_items=2, max_items=2, description="[longitude, latitude]")

class GeoJSONFeature(BaseModel):
    """GeoJSON Feature"""
    type: str = Field(default="Feature")
    geometry: GeoJSONPoint
    properties: Dict[str, Any]

class FloodReadingGeoJSON(BaseModel):
    """Flood reading in GeoJSON format"""
    type: str = Field(default="Feature")
    geometry: GeoJSONPoint
    properties: Dict[str, Any] = Field(..., description="Flood reading properties")
    
    @classmethod
    def from_flood_reading(cls, reading) -> "FloodReadingGeoJSON":
        """Convert FloodReading to GeoJSON format"""
        return cls(
            geometry=GeoJSONPoint(coordinates=[reading.location_lng, reading.location_lat]),
            properties={
                "id": reading.id,
                "sensor_id": reading.sensor_id,
                "water_level_cm": reading.water_level_cm,
                "rainfall_mm": reading.rainfall_mm,
                "risk_level": reading.risk_level,
                "timestamp": reading.timestamp.isoformat(),
                "notes": reading.notes,
                "layer": "flood_readings"
            }
        )

class EmergencyReportGeoJSON(BaseModel):
    """Emergency report in GeoJSON format"""
    type: str = Field(default="Feature")
    geometry: GeoJSONPoint
    properties: Dict[str, Any] = Field(..., description="Emergency report properties")
    
    @classmethod
    def from_emergency_report(cls, report) -> "EmergencyReportGeoJSON":
        """Convert EmergencyReport to GeoJSON format"""
        return cls(
            geometry=GeoJSONPoint(coordinates=[report.location_lng, report.location_lat]),
            properties={
                "id": report.id,
                "title": report.title,
                "description": report.description,
                "severity": report.severity,
                "category": report.category,
                "status": report.status,
                "user_id": report.user_id,
                "submitted_at": report.submitted_at.isoformat(),
                "triaged_at": report.triaged_at.isoformat() if report.triaged_at else None,
                "triaged_by": report.triaged_by,
                "triage_notes": report.triage_notes,
                "contact_phone": report.contact_phone,
                "layer": "emergency_reports"
            }
        )

class EvacuationCenterGeoJSON(BaseModel):
    """Evacuation center in GeoJSON format"""
    type: str = Field(default="Feature")
    geometry: GeoJSONPoint
    properties: Dict[str, Any] = Field(..., description="Evacuation center properties")
    
    @classmethod
    def from_evacuation_center(cls, center) -> "EvacuationCenterGeoJSON":
        """Convert EvacuationCenter to GeoJSON format"""
        return cls(
            geometry=GeoJSONPoint(coordinates=[center.location_lng, center.location_lat]),
            properties={
                "id": center.id,
                "name": center.name,
                "capacity": center.capacity,
                "current_occupancy": center.current_occupancy,
                "available_capacity": center.capacity - center.current_occupancy,
                "occupancy_percentage": (center.current_occupancy / center.capacity * 100) if center.capacity > 0 else 0,
                "contact_info": center.contact_info,
                "is_active": center.is_active,
                "created_at": center.created_at.isoformat(),
                "updated_at": center.updated_at.isoformat() if center.updated_at else None,
                "layer": "evacuation_centers"
            }
        )

class EvacuationCenterWithDistance(BaseModel):
    """Evacuation center with distance information"""
    id: int
    name: str
    location_lat: float
    location_lng: float
    capacity: int
    current_occupancy: int
    available_capacity: int
    occupancy_percentage: float
    contact_info: Optional[str]
    is_active: bool
    distance_km: float = Field(..., description="Distance in kilometers")
    distance_meters: float = Field(..., description="Distance in meters")
    
    @classmethod
    def from_center_with_distance(cls, center, distance_meters: float) -> "EvacuationCenterWithDistance":
        """Create from evacuation center with distance"""
        return cls(
            id=center.id,
            name=center.name,
            location_lat=center.location_lat,
            location_lng=center.location_lng,
            capacity=center.capacity,
            current_occupancy=center.current_occupancy,
            available_capacity=center.capacity - center.current_occupancy,
            occupancy_percentage=(center.current_occupancy / center.capacity * 100) if center.capacity > 0 else 0,
            contact_info=center.contact_info,
            is_active=center.is_active,
            distance_km=distance_meters / 1000,
            distance_meters=distance_meters
        )

class MapDataResponse(BaseModel):
    """Unified map data response"""
    flood_readings: List[FloodReadingGeoJSON] = Field(default_factory=list)
    emergency_reports: List[EmergencyReportGeoJSON] = Field(default_factory=list)
    evacuation_centers: List[EvacuationCenterGeoJSON] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_count: int = Field(..., description="Total number of features returned")
    bounds: MapBounds = Field(..., description="Requested map bounds")
    zoom_level: int = Field(..., description="Requested zoom level")

class RouteSafetyAssessment(BaseModel):
    """Route safety assessment"""
    is_safe: bool = Field(..., description="Whether the route is safe")
    risk_level: str = Field(..., description="Overall risk level: LOW, MEDIUM, HIGH, CRITICAL")
    flood_affected_segments: List[Dict[str, Any]] = Field(default_factory=list)
    alternative_routes: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_travel_time: Optional[int] = Field(None, description="Estimated travel time in minutes")
    warnings: List[str] = Field(default_factory=list)

class FloodAffectedArea(BaseModel):
    """Flood affected area information"""
    id: int
    name: str
    severity: str
    affected_area_km2: float
    population_at_risk: Optional[int]
    evacuation_centers_nearby: int
    last_updated: datetime
    geometry: GeoJSONPoint