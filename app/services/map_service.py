from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.models.flood_data import FloodReading
from app.models.emergency_report import EmergencyReport
from app.models.evacuation_center import EvacuationCenter
from app.schemas.map import (
    MapBounds, 
    FloodReadingGeoJSON, 
    EmergencyReportGeoJSON, 
    EvacuationCenterGeoJSON,
    EvacuationCenterWithDistance,
    RouteSafetyAssessment
)
from app.repositories.geospatial_repository import GeospatialRepository
import logging

logger = logging.getLogger(__name__)

class MapService:
    """Service for map-related operations and geospatial queries"""
    
    def __init__(self):
        self.geospatial_repo = GeospatialRepository()
    
    async def get_map_data(
        self, 
        bounds: MapBounds, 
        zoom_level: int, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get all map data within the specified bounds"""
        try:
            # Get flood readings within bounds
            flood_readings = await self._get_flood_readings_in_bounds(bounds, session)
            
            # Get emergency reports within bounds
            emergency_reports = await self._get_emergency_reports_in_bounds(bounds, session)
            
            # Get evacuation centers within bounds
            evacuation_centers = await self._get_evacuation_centers_in_bounds(bounds, session)
            
            # Convert to GeoJSON format
            flood_geojson = [FloodReadingGeoJSON.from_flood_reading(reading) for reading in flood_readings]
            reports_geojson = [EmergencyReportGeoJSON.from_emergency_report(report) for report in emergency_reports]
            centers_geojson = [EvacuationCenterGeoJSON.from_evacuation_center(center) for center in evacuation_centers]
            
            total_count = len(flood_geojson) + len(reports_geojson) + len(centers_geojson)
            
            return {
                "flood_readings": flood_geojson,
                "emergency_reports": reports_geojson,
                "evacuation_centers": centers_geojson,
                "last_updated": datetime.utcnow(),
                "total_count": total_count,
                "bounds": bounds,
                "zoom_level": zoom_level
            }
            
        except Exception as e:
            logger.error(f"Error getting map data: {str(e)}")
            raise
    
    async def _get_flood_readings_in_bounds(
        self, 
        bounds: MapBounds, 
        session: AsyncSession
    ) -> List[FloodReading]:
        """Get flood readings within map bounds using PostGIS"""
        try:
            # Use PostGIS ST_Within for efficient bounds filtering
            query = text("""
                SELECT fr.*
                FROM floodreading fr
                WHERE fr.location_geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
                AND ST_Within(fr.location_geom, ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326))
                ORDER BY fr.timestamp DESC
                LIMIT 1000
            """)
            
            result = await session.execute(
                query,
                {
                    "min_lat": bounds.south,
                    "max_lat": bounds.north,
                    "min_lng": bounds.west,
                    "max_lng": bounds.east
                }
            )
            
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting flood readings in bounds: {str(e)}")
            return []
    
    async def _get_emergency_reports_in_bounds(
        self, 
        bounds: MapBounds, 
        session: AsyncSession
    ) -> List[EmergencyReport]:
        """Get emergency reports within map bounds using PostGIS"""
        try:
            query = text("""
                SELECT er.*
                FROM emergencyreport er
                WHERE er.location_geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
                AND ST_Within(er.location_geom, ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326))
                ORDER BY er.submitted_at DESC
                LIMIT 1000
            """)
            
            result = await session.execute(
                query,
                {
                    "min_lat": bounds.south,
                    "max_lat": bounds.north,
                    "min_lng": bounds.west,
                    "max_lng": bounds.east
                }
            )
            
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting emergency reports in bounds: {str(e)}")
            return []
    
    async def _get_evacuation_centers_in_bounds(
        self, 
        bounds: MapBounds, 
        session: AsyncSession
    ) -> List[EvacuationCenter]:
        """Get evacuation centers within map bounds using PostGIS"""
        try:
            query = text("""
                SELECT ec.*
                FROM evacuationcenter ec
                WHERE ec.location_geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
                AND ST_Within(ec.location_geom, ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326))
                AND ec.is_active = true
                ORDER BY ec.name
            """)
            
            result = await session.execute(
                query,
                {
                    "min_lat": bounds.south,
                    "max_lat": bounds.north,
                    "min_lng": bounds.west,
                    "max_lng": bounds.east
                }
            )
            
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting evacuation centers in bounds: {str(e)}")
            return []
    
    async def find_nearest_evacuation_centers(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float, 
        min_capacity: int = 0,
        session: AsyncSession = None
    ) -> List[EvacuationCenterWithDistance]:
        """Find nearest evacuation centers using PostGIS spatial queries"""
        try:
            # Use PostGIS ST_DWithin for efficient proximity search
            query = text("""
                SELECT 
                    ec.*,
                    ST_Distance(
                        ec.location_geom::geography, 
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                    ) as distance_meters
                FROM evacuationcenter ec
                WHERE ST_DWithin(
                    ec.location_geom::geography, 
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 
                    :radius_meters
                )
                AND ec.is_active = true
                AND (ec.capacity - ec.current_occupancy) >= :min_capacity
                ORDER BY distance_meters
                LIMIT 20
            """)
            
            result = await session.execute(
                query,
                {
                    "lat": lat,
                    "lng": lng,
                    "radius_meters": radius_km * 1000,
                    "min_capacity": min_capacity
                }
            )
            
            centers_with_distance = []
            for row in result:
                center = EvacuationCenter(
                    id=row.id,
                    name=row.name,
                    location_lat=row.location_lat,
                    location_lng=row.location_lng,
                    capacity=row.capacity,
                    current_occupancy=row.current_occupancy,
                    contact_info=row.contact_info,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
                centers_with_distance.append(
                    EvacuationCenterWithDistance.from_center_with_distance(center, row.distance_meters)
                )
            
            return centers_with_distance
            
        except Exception as e:
            logger.error(f"Error finding nearest evacuation centers: {str(e)}")
            return []
    
    async def calculate_route_safety(
        self, 
        start_lat: float, 
        start_lng: float, 
        end_lat: float, 
        end_lng: float, 
        session: AsyncSession
    ) -> RouteSafetyAssessment:
        """Calculate route safety considering flood conditions"""
        try:
            # Check for flood readings along the route
            # This is a simplified implementation - in production, you'd use proper routing algorithms
            query = text("""
                SELECT 
                    fr.*,
                    ST_Distance(
                        fr.location_geom::geography,
                        ST_SetSRID(ST_MakePoint(:start_lng, :start_lat), 4326)::geography
                    ) as distance_from_start,
                    ST_Distance(
                        fr.location_geom::geography,
                        ST_SetSRID(ST_MakePoint(:end_lng, :end_lat), 4326)::geography
                    ) as distance_from_end
                FROM floodreading fr
                WHERE fr.timestamp >= NOW() - INTERVAL '24 hours'
                AND (
                    ST_DWithin(
                        fr.location_geom::geography,
                        ST_SetSRID(ST_MakePoint(:start_lng, :start_lat), 4326)::geography,
                        5000
                    )
                    OR ST_DWithin(
                        fr.location_geom::geography,
                        ST_SetSRID(ST_MakePoint(:end_lng, :end_lat), 4326)::geography,
                        5000
                    )
                )
                ORDER BY fr.risk_level DESC, fr.timestamp DESC
            """)
            
            result = await session.execute(
                query,
                {
                    "start_lat": start_lat,
                    "start_lng": start_lng,
                    "end_lat": end_lat,
                    "end_lng": end_lng
                }
            )
            
            flood_readings = list(result.scalars().all())
            
            # Determine overall risk level
            risk_levels = [reading.risk_level for reading in flood_readings]
            if "CRITICAL" in risk_levels:
                overall_risk = "CRITICAL"
            elif "HIGH" in risk_levels:
                overall_risk = "HIGH"
            elif "MODERATE" in risk_levels:
                overall_risk = "MEDIUM"
            else:
                overall_risk = "LOW"
            
            is_safe = overall_risk in ["LOW", "MEDIUM"]
            
            warnings = []
            if not is_safe:
                warnings.append(f"Route may be affected by {overall_risk.lower()} flood conditions")
                warnings.append("Consider alternative routes or evacuation centers")
            
            return RouteSafetyAssessment(
                is_safe=is_safe,
                risk_level=overall_risk,
                flood_affected_segments=[
                    {
                        "location": {"lat": reading.location_lat, "lng": reading.location_lng},
                        "risk_level": reading.risk_level,
                        "water_level_cm": reading.water_level_cm,
                        "timestamp": reading.timestamp.isoformat()
                    }
                    for reading in flood_readings
                ],
                alternative_routes=[],  # Would be populated by routing service
                estimated_travel_time=None,  # Would be calculated by routing service
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error calculating route safety: {str(e)}")
            return RouteSafetyAssessment(
                is_safe=False,
                risk_level="UNKNOWN",
                warnings=["Unable to assess route safety"]
            )
    
    async def get_flood_affected_areas(
        self, 
        bounds: MapBounds, 
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get flood affected areas within bounds"""
        try:
            # This would typically involve more complex spatial analysis
            # For now, we'll return areas with high flood readings
            query = text("""
                SELECT 
                    ST_ClusterDBSCAN(fr.location_geom, 1000, 3) OVER() as cluster_id,
                    fr.*
                FROM floodreading fr
                WHERE fr.location_geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
                AND fr.risk_level IN ('HIGH', 'CRITICAL')
                AND fr.timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY cluster_id, fr.timestamp DESC
            """)
            
            result = await session.execute(
                query,
                {
                    "min_lat": bounds.south,
                    "max_lat": bounds.north,
                    "min_lng": bounds.west,
                    "max_lng": bounds.east
                }
            )
            
            # Group by cluster and return affected areas
            clusters = {}
            for row in result:
                cluster_id = row.cluster_id
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(row)
            
            affected_areas = []
            for cluster_id, readings in clusters.items():
                if len(readings) >= 3:  # Minimum readings to form an affected area
                    avg_lat = sum(r.location_lat for r in readings) / len(readings)
                    avg_lng = sum(r.location_lng for r in readings) / len(readings)
                    max_risk = max(r.risk_level for r in readings)
                    
                    affected_areas.append({
                        "id": cluster_id,
                        "name": f"Flood Affected Area {cluster_id}",
                        "severity": max_risk,
                        "center": {"lat": avg_lat, "lng": avg_lng},
                        "readings_count": len(readings),
                        "last_updated": max(r.timestamp for r in readings).isoformat()
                    })
            
            return affected_areas
            
        except Exception as e:
            logger.error(f"Error getting flood affected areas: {str(e)}")
            return []
    
    def _convert_to_geojson(self, obj, layer_type: str) -> Dict[str, Any]:
        """Convert model object to GeoJSON format"""
        if layer_type == "flood_readings":
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [obj.location_lng, obj.location_lat]
                },
                "properties": {
                    "id": obj.id,
                    "sensor_id": obj.sensor_id,
                    "water_level_cm": obj.water_level_cm,
                    "rainfall_mm": obj.rainfall_mm,
                    "risk_level": obj.risk_level,
                    "timestamp": obj.timestamp.isoformat(),
                    "notes": obj.notes,
                    "layer": "flood_readings"
                }
            }
        elif layer_type == "emergency_reports":
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [obj.location_lng, obj.location_lat]
                },
                "properties": {
                    "id": obj.id,
                    "title": obj.title,
                    "description": obj.description,
                    "severity": obj.severity,
                    "category": obj.category,
                    "status": obj.status,
                    "user_id": obj.user_id,
                    "submitted_at": obj.submitted_at.isoformat(),
                    "triaged_at": obj.triaged_at.isoformat() if obj.triaged_at else None,
                    "triaged_by": obj.triaged_by,
                    "triage_notes": obj.triage_notes,
                    "contact_phone": obj.contact_phone,
                    "layer": "emergency_reports"
                }
            }
        elif layer_type == "evacuation_centers":
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [obj.location_lng, obj.location_lat]
                },
                "properties": {
                    "id": obj.id,
                    "name": obj.name,
                    "capacity": obj.capacity,
                    "current_occupancy": obj.current_occupancy,
                    "available_capacity": obj.capacity - obj.current_occupancy,
                    "occupancy_percentage": (obj.current_occupancy / obj.capacity * 100) if obj.capacity > 0 else 0,
                    "contact_info": obj.contact_info,
                    "is_active": obj.is_active,
                    "created_at": obj.created_at.isoformat(),
                    "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
                    "layer": "evacuation_centers"
                }
            }
        else:
            raise ValueError(f"Unknown layer type: {layer_type}")
