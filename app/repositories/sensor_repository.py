from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.sensor_data import Sensor, SensorHealth
from app.models.flood_data import FloodReading
from app.repositories.base_repository import BaseRepository


class SensorRepository(BaseRepository[Sensor]):
    """Repository for sensor device operations"""
    
    def __init__(self):
        super().__init__(Sensor)
    
    async def get_by_sensor_id(self, sensor_id: str, session: AsyncSession) -> Optional[Sensor]:
        """Get a specific sensor by ID"""
        result = await session.execute(
            select(Sensor).where(Sensor.sensor_id == sensor_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_sensors(self, session: AsyncSession) -> List[Sensor]:
        """Get all active sensors"""
        result = await session.execute(
            select(Sensor).where(Sensor.is_active == True)
        )
        return result.scalars().all()
    
    async def get_sensors_by_status(self, status: str, session: AsyncSession) -> List[Sensor]:
        """Get sensors by status"""
        result = await session.execute(
            select(Sensor).where(Sensor.status == status)
        )
        return result.scalars().all()
    
    async def get_sensors_by_location_range(
        self, 
        lat_min: float, 
        lat_max: float, 
        lng_min: float, 
        lng_max: float, 
        session: AsyncSession
    ) -> List[Sensor]:
        """Get sensors within a geographic range"""
        result = await session.execute(
            select(Sensor)
            .where(
                Sensor.location_lat >= lat_min,
                Sensor.location_lat <= lat_max,
                Sensor.location_lng >= lng_min,
                Sensor.location_lng <= lng_max
            )
        )
        return result.scalars().all()
    
    async def get_sensor_readings(self, sensor_id: str, session: AsyncSession) -> List[FloodReading]:
        """Get all readings for a specific sensor"""
        result = await session.execute(
            select(FloodReading).where(FloodReading.sensor_id == sensor_id)
        )
        return result.scalars().all()
    
    async def get_latest_reading_by_sensor(self, sensor_id: str, session: AsyncSession) -> Optional[FloodReading]:
        """Get the latest reading for a specific sensor"""
        result = await session.execute(
            select(FloodReading)
            .where(FloodReading.sensor_id == sensor_id)
            .order_by(FloodReading.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

