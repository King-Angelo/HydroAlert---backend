from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.flood_data import FloodReading
from app.models.emergency_report import EmergencyReport
from app.models.evacuation_center import EvacuationCenter, EvacuationCenterWithDistance
from .base_repository import BaseRepository

class GeospatialRepository:
    """Repository for PostGIS geospatial queries"""
    
    async def get_alerts_within_radius(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float, 
        session: AsyncSession
    ) -> List[FloodReading]:
        """Get flood alerts within radius using PostGIS ST_DWithin"""
        query = text("""
            SELECT fr.*, 
                   ST_Distance(
                       fr.location_geom::geography, 
                       ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                   ) as distance_m
            FROM floodreading fr
            WHERE ST_DWithin(
                fr.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 
                :radius_meters
            )
            ORDER BY ST_Distance(
                fr.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            )
        """)
        
        result = await session.execute(
            query, 
            {
                "lat": lat, 
                "lng": lng, 
                "radius_meters": radius_km * 1000
            }
        )
        return result.fetchall()
    
    async def get_reports_within_radius(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float, 
        session: AsyncSession
    ) -> List[EmergencyReport]:
        """Get emergency reports within radius using PostGIS"""
        query = text("""
            SELECT er.*, 
                   ST_Distance(
                       er.location_geom::geography, 
                       ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                   ) as distance_m
            FROM emergencyreport er
            WHERE ST_DWithin(
                er.location_geom::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :radius_meters
            )
            ORDER BY ST_Distance(
                er.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            )
        """)
        
        result = await session.execute(
            query,
            {
                "lat": lat,
                "lng": lng, 
                "radius_meters": radius_km * 1000
            }
        )
        return result.fetchall()
    
    async def get_evacuation_centers_near_point(
        self, 
        lat: float, 
        lng: float, 
        max_distance_km: float,
        session: AsyncSession
    ) -> List[EvacuationCenterWithDistance]:
        """Find evacuation centers near a point with distance calculation"""
        query = text("""
            SELECT ec.*, 
                   ST_Distance(ec.location_geom::geography, 
                              ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m
            FROM evacuationcenter ec
            WHERE ST_DWithin(
                ec.location_geom::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :max_distance_meters
            )
            AND ec.is_active = true
            ORDER BY ST_Distance(
                ec.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            )
        """)
        
        result = await session.execute(
            query,
            {
                "lat": lat,
                "lng": lng, 
                "max_distance_meters": max_distance_km * 1000
            }
        )
        return result.fetchall()
    
    async def get_evacuation_centers_with_capacity(
        self, 
        lat: float, 
        lng: float, 
        max_distance_km: float,
        min_capacity: int,
        session: AsyncSession
    ) -> List[EvacuationCenterWithDistance]:
        """Find evacuation centers with available capacity near a point"""
        query = text("""
            SELECT ec.*, 
                   ST_Distance(ec.location_geom::geography, 
                              ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m
            FROM evacuationcenter ec
            WHERE ST_DWithin(
                ec.location_geom::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :max_distance_meters
            )
            AND ec.is_active = true
            AND (ec.capacity - ec.current_occupancy) >= :min_capacity
            ORDER BY ST_Distance(
                ec.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            )
        """)
        
        result = await session.execute(
            query,
            {
                "lat": lat,
                "lng": lng, 
                "max_distance_meters": max_distance_km * 1000,
                "min_capacity": min_capacity
            }
        )
        return result.fetchall()
    
    async def get_alerts_in_polygon(
        self, 
        polygon_wkt: str, 
        session: AsyncSession
    ) -> List[FloodReading]:
        """Get alerts within a polygon area"""
        query = text("""
            SELECT fr.*
            FROM floodreading fr
            WHERE ST_Within(
                fr.location_geom,
                ST_GeomFromText(:polygon_wkt, 4326)
            )
            ORDER BY fr.timestamp DESC
        """)
        
        result = await session.execute(
            query,
            {"polygon_wkt": polygon_wkt}
        )
        return result.fetchall()
    
    async def get_nearest_evacuation_center(
        self, 
        lat: float, 
        lng: float,
        session: AsyncSession
    ) -> Optional[EvacuationCenterWithDistance]:
        """Get the nearest evacuation center to a point"""
        query = text("""
            SELECT ec.*, 
                   ST_Distance(ec.location_geom::geography, 
                              ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m
            FROM evacuationcenter ec
            WHERE ec.is_active = true
            ORDER BY ST_Distance(
                ec.location_geom::geography, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            )
            LIMIT 1
        """)
        
        result = await session.execute(
            query,
            {
                "lat": lat,
                "lng": lng
            }
        )
        return result.fetchone()
