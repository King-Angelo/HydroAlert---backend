from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from app.models.flood_data import FloodReading, RiskLevel, calculate_risk_level
from app.repositories.geospatial_repository import GeospatialRepository
import logging

logger = logging.getLogger(__name__)

class FloodService:
    def __init__(self):
        self.geospatial_repo = GeospatialRepository()

    async def create_reading(self, reading: FloodReading, session: AsyncSession) -> FloodReading:
        """Create a new flood reading"""
        try:
            # Ensure risk level is calculated
            if not reading.risk_level:
                reading.risk_level = calculate_risk_level(
                    reading.water_level_cm, 
                    reading.rainfall_mm
                )
            
            # Create PostGIS geometry if not present
            if not reading.location_geom and reading.location_lat and reading.location_lng:
                reading.location_geom = f"POINT({reading.location_lng} {reading.location_lat})"
            
            session.add(reading)
            await session.commit()
            await session.refresh(reading)
            
            logger.info(f"Created flood reading for sensor {reading.sensor_id}: {reading.risk_level.value}")
            return reading
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating flood reading: {e}")
            raise

    async def get_recent_readings(
        self, 
        session: AsyncSession, 
        limit: int = 100,
        sensor_id: Optional[str] = None
    ) -> List[FloodReading]:
        """Get recent flood readings"""
        try:
            query = select(FloodReading)
            
            if sensor_id:
                query = query.where(FloodReading.sensor_id == sensor_id)
            
            query = query.order_by(desc(FloodReading.timestamp)).limit(limit)
            
            result = await session.execute(query)
            readings = result.scalars().all()
            
            return readings
        except Exception as e:
            logger.error(f"Error getting recent readings: {e}")
            raise

    async def get_readings_by_location(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float, 
        session: AsyncSession
    ) -> List[FloodReading]:
        """Get flood readings within a radius using PostGIS"""
        try:
            return await self.geospatial_repo.get_flood_readings_within_radius(
                lat, lng, radius_km, session
            )
        except Exception as e:
            logger.error(f"Error getting readings by location: {e}")
            raise

    async def get_readings_by_risk_level(
        self, 
        risk_level: RiskLevel, 
        session: AsyncSession,
        limit: int = 100
    ) -> List[FloodReading]:
        """Get readings filtered by risk level"""
        try:
            query = (
                select(FloodReading)
                .where(FloodReading.risk_level == risk_level)
                .order_by(desc(FloodReading.timestamp))
                .limit(limit)
            )
            
            result = await session.execute(query)
            readings = result.scalars().all()
            
            return readings
        except Exception as e:
            logger.error(f"Error getting readings by risk level: {e}")
            raise

    async def get_critical_readings(
        self, 
        session: AsyncSession, 
        hours: int = 24
    ) -> List[FloodReading]:
        """Get critical risk readings from the last N hours"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = (
                select(FloodReading)
                .where(
                    and_(
                        FloodReading.risk_level == RiskLevel.CRITICAL,
                        FloodReading.timestamp >= since
                    )
                )
                .order_by(desc(FloodReading.timestamp))
            )
            
            result = await session.execute(query)
            readings = result.scalars().all()
            
            return readings
        except Exception as e:
            logger.error(f"Error getting critical readings: {e}")
            raise

    async def get_latest_sensor_reading(
        self, 
        sensor_id: str, 
        session: AsyncSession
    ) -> Optional[FloodReading]:
        """Get the latest reading for a specific sensor"""
        try:
            query = (
                select(FloodReading)
                .where(FloodReading.sensor_id == sensor_id)
                .order_by(desc(FloodReading.timestamp))
                .limit(1)
            )
            
            result = await session.execute(query)
            reading = result.scalar_one_or_none()
            
            return reading
        except Exception as e:
            logger.error(f"Error getting latest reading for sensor {sensor_id}: {e}")
            raise