from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.flood_data import FloodReading
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[FloodReading]):
    """Repository for flood alert operations"""
    
    def __init__(self):
        super().__init__(FloodReading)
    
    async def get_active_alerts(self, session: AsyncSession) -> List[FloodReading]:
        """Get all active flood alerts (high and critical risk levels)"""
        result = await session.execute(
            select(FloodReading)
            .where(
                (FloodReading.risk_level == "HIGH") | 
                (FloodReading.risk_level == "CRITICAL")
            )
            .order_by(FloodReading.timestamp.desc())
        )
        return result.scalars().all()
    
    async def get_by_location(self, lat: float, lng: float, session: AsyncSession, radius_km: float = 10) -> List[FloodReading]:
        """Get alerts for a specific location using PostGIS ST_DWithin"""
        from sqlalchemy import text
        
        query = text("""
            SELECT fr.*
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
        return list(result.scalars().all())
    
    async def get_by_risk_level(self, risk_level: str, session: AsyncSession) -> List[FloodReading]:
        """Get alerts by risk level"""
        result = await session.execute(
            select(FloodReading)
            .where(FloodReading.risk_level == risk_level)
            .order_by(FloodReading.timestamp.desc())
        )
        return result.scalars().all()
    
    async def get_recent_alerts(self, hours: int, session: AsyncSession) -> List[FloodReading]:
        """Get alerts from the last N hours"""
        from datetime import datetime, timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        result = await session.execute(
            select(FloodReading)
            .where(FloodReading.timestamp >= cutoff_time)
            .order_by(FloodReading.timestamp.desc())
        )
        return result.scalars().all()
