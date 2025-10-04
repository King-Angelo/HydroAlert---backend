from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from app.models.sensor_data import (
    Sensor, SensorHealth, SensorCreate, SensorUpdate, SensorResponse, 
    SensorHealthResponse, SensorSummary, SensorStatus, SensorHealthCreate
)
from app.models.flood_data import FloodReading
from app.repositories.geospatial_repository import GeospatialRepository
import logging

logger = logging.getLogger(__name__)

class SensorService:
    def __init__(self):
        self.geospatial_repo = GeospatialRepository()

    async def get_all_sensors(
        self, 
        session: AsyncSession, 
        status_filter: Optional[SensorStatus] = None,
        active_only: bool = True
    ) -> List[SensorResponse]:
        """Get all sensors with optional filtering"""
        try:
            query = select(Sensor)
            
            if active_only:
                query = query.where(Sensor.is_active == True)
            
            if status_filter:
                query = query.where(Sensor.status == status_filter)
            
            query = query.order_by(desc(Sensor.last_reading_time), Sensor.name)
            
            result = await session.execute(query)
            sensors = result.scalars().all()
            
            return [self._convert_to_response(sensor) for sensor in sensors]
        except Exception as e:
            logger.error(f"Error getting all sensors: {e}")
            raise

    async def get_sensor_by_id(self, sensor_id: str, session: AsyncSession) -> Optional[SensorResponse]:
        """Get a specific sensor by ID"""
        try:
            query = select(Sensor).where(Sensor.sensor_id == sensor_id)
            result = await session.execute(query)
            sensor = result.scalar_one_or_none()
            
            if sensor:
                return self._convert_to_response(sensor)
            return None
        except Exception as e:
            logger.error(f"Error getting sensor {sensor_id}: {e}")
            raise

    async def create_sensor(self, sensor_data: SensorCreate, session: AsyncSession) -> SensorResponse:
        """Create a new sensor"""
        try:
            # Create PostGIS geometry
            location_geom = f"POINT({sensor_data.location_lng} {sensor_data.location_lat})"
            
            db_sensor = Sensor(
                sensor_id=sensor_data.sensor_id,
                name=sensor_data.name,
                description=sensor_data.description,
                sensor_type=sensor_data.sensor_type,
                location_lat=sensor_data.location_lat,
                location_lng=sensor_data.location_lng,
                location_geom=location_geom,
                location_description=sensor_data.location_description,
                reading_interval_minutes=sensor_data.reading_interval_minutes,
                battery_low_threshold=sensor_data.battery_low_threshold,
                signal_low_threshold=sensor_data.signal_low_threshold,
                status=SensorStatus.ACTIVE,
                is_active=True
            )
            
            session.add(db_sensor)
            await session.commit()
            await session.refresh(db_sensor)
            
            logger.info(f"Created new sensor: {sensor_data.sensor_id}")
            return self._convert_to_response(db_sensor)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating sensor {sensor_data.sensor_id}: {e}")
            raise

    async def update_sensor(
        self, 
        sensor_id: str, 
        sensor_update: SensorUpdate, 
        session: AsyncSession
    ) -> SensorResponse:
        """Update sensor information"""
        try:
            query = select(Sensor).where(Sensor.sensor_id == sensor_id)
            result = await session.execute(query)
            sensor = result.scalar_one_or_none()
            
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")
            
            # Update fields
            update_data = sensor_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(sensor, field):
                    setattr(sensor, field, value)
            
            # Update PostGIS geometry if location changed
            if sensor_update.location_lat is not None or sensor_update.location_lng is not None:
                lat = sensor_update.location_lat or sensor.location_lat
                lng = sensor_update.location_lng or sensor.location_lng
                sensor.location_geom = f"POINT({lng} {lat})"
            
            sensor.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(sensor)
            
            logger.info(f"Updated sensor: {sensor_id}")
            return self._convert_to_response(sensor)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating sensor {sensor_id}: {e}")
            raise

    async def deactivate_sensor(self, sensor_id: str, session: AsyncSession) -> bool:
        """Deactivate a sensor (soft delete)"""
        try:
            query = select(Sensor).where(Sensor.sensor_id == sensor_id)
            result = await session.execute(query)
            sensor = result.scalar_one_or_none()
            
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")
            
            sensor.is_active = False
            sensor.status = SensorStatus.INACTIVE
            sensor.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Deactivated sensor: {sensor_id}")
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deactivating sensor {sensor_id}: {e}")
            raise

    async def get_sensor_health_history(
        self, 
        sensor_id: str, 
        session: AsyncSession, 
        since: Optional[datetime] = None
    ) -> List[SensorHealthResponse]:
        """Get sensor health history"""
        try:
            query = select(SensorHealth).where(SensorHealth.sensor_id == sensor_id)
            
            if since:
                query = query.where(SensorHealth.recorded_at >= since)
            
            query = query.order_by(desc(SensorHealth.recorded_at))
            
            result = await session.execute(query)
            health_logs = result.scalars().all()
            
            return [self._convert_health_to_response(health) for health in health_logs]
        except Exception as e:
            logger.error(f"Error getting health history for sensor {sensor_id}: {e}")
            raise

    async def get_latest_sensor_health(
        self, 
        sensor_id: str, 
        session: AsyncSession
    ) -> Optional[SensorHealthResponse]:
        """Get the latest health record for a sensor"""
        try:
            query = (
                select(SensorHealth)
                .where(SensorHealth.sensor_id == sensor_id)
                .order_by(desc(SensorHealth.recorded_at))
                .limit(1)
            )
            
            result = await session.execute(query)
            health = result.scalar_one_or_none()
            
            if health:
                return self._convert_health_to_response(health)
            return None
        except Exception as e:
            logger.error(f"Error getting latest health for sensor {sensor_id}: {e}")
            raise

    async def create_health_log(
        self, 
        health_data: SensorHealthCreate, 
        session: AsyncSession
    ) -> SensorHealthResponse:
        """Create a new health log entry"""
        try:
            db_health = SensorHealth(
                sensor_id=health_data.sensor_id,
                battery_level=health_data.battery_level,
                signal_strength=health_data.signal_strength,
                status=health_data.status,
                temperature_celsius=health_data.temperature_celsius,
                humidity_percent=health_data.humidity_percent,
                notes=health_data.notes,
                recorded_at=datetime.utcnow()
            )
            
            session.add(db_health)
            await session.commit()
            await session.refresh(db_health)
            
            logger.info(f"Created health log for sensor: {health_data.sensor_id}")
            return self._convert_health_to_response(db_health)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating health log for sensor {health_data.sensor_id}: {e}")
            raise

    async def update_sensor_health_from_reading(
        self,
        sensor_id: str,
        battery_level: Optional[int],
        signal_strength: Optional[int],
        temperature_celsius: Optional[float],
        humidity_percent: Optional[float],
        session: AsyncSession
    ) -> bool:
        """Update sensor metadata from reading data"""
        try:
            query = select(Sensor).where(Sensor.sensor_id == sensor_id)
            result = await session.execute(query)
            sensor = result.scalar_one_or_none()
            
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")
            
            # Update sensor metadata
            if battery_level is not None:
                sensor.battery_level = battery_level
            if signal_strength is not None:
                sensor.signal_strength = signal_strength
            
            sensor.last_reading_time = datetime.utcnow()
            sensor.updated_at = datetime.utcnow()
            
            # Update status based on health metrics
            if battery_level is not None and battery_level <= sensor.battery_low_threshold:
                sensor.status = SensorStatus.ERROR
            elif signal_strength is not None and signal_strength <= sensor.signal_low_threshold:
                sensor.status = SensorStatus.ERROR
            elif sensor.status == SensorStatus.ERROR and (
                (battery_level is None or battery_level > sensor.battery_low_threshold) and
                (signal_strength is None or signal_strength > sensor.signal_low_threshold)
            ):
                sensor.status = SensorStatus.ACTIVE
            
            # Create health log entry
            health_log = SensorHealth(
                sensor_id=sensor_id,
                battery_level=battery_level,
                signal_strength=signal_strength,
                status=sensor.status,
                temperature_celsius=temperature_celsius,
                humidity_percent=humidity_percent,
                recorded_at=datetime.utcnow()
            )
            
            session.add(health_log)
            await session.commit()
            
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating sensor health for {sensor_id}: {e}")
            raise

    async def get_sensor_readings(
        self, 
        sensor_id: str, 
        session: AsyncSession, 
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get sensor readings for analysis"""
        try:
            query = select(FloodReading).where(FloodReading.sensor_id == sensor_id)
            
            if since:
                query = query.where(FloodReading.timestamp >= since)
            
            query = query.order_by(desc(FloodReading.timestamp))
            
            result = await session.execute(query)
            readings = result.scalars().all()
            
            return [
                {
                    "id": reading.id,
                    "sensor_id": reading.sensor_id,
                    "water_level_cm": reading.water_level_cm,
                    "rainfall_mm": reading.rainfall_mm,
                    "risk_level": reading.risk_level.value,
                    "timestamp": reading.timestamp.isoformat(),
                    "notes": reading.notes
                }
                for reading in readings
            ]
        except Exception as e:
            logger.error(f"Error getting readings for sensor {sensor_id}: {e}")
            raise

    async def record_maintenance(
        self, 
        sensor_id: str, 
        maintenance_notes: str, 
        session: AsyncSession
    ) -> bool:
        """Record maintenance performed on a sensor"""
        try:
            query = select(Sensor).where(Sensor.sensor_id == sensor_id)
            result = await session.execute(query)
            sensor = result.scalar_one_or_none()
            
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")
            
            sensor.last_maintenance = datetime.utcnow()
            sensor.updated_at = datetime.utcnow()
            
            # Create health log entry for maintenance
            health_log = SensorHealth(
                sensor_id=sensor_id,
                battery_level=sensor.battery_level,
                signal_strength=sensor.signal_strength,
                status=sensor.status,
                notes=f"Maintenance performed: {maintenance_notes}",
                recorded_at=datetime.utcnow()
            )
            
            session.add(health_log)
            await session.commit()
            
            logger.info(f"Recorded maintenance for sensor {sensor_id}: {maintenance_notes}")
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Error recording maintenance for sensor {sensor_id}: {e}")
            raise

    async def get_sensor_summary(self, session: AsyncSession) -> SensorSummary:
        """Get sensor summary statistics"""
        try:
            # Get total sensors
            total_query = select(func.count(Sensor.id))
            total_result = await session.execute(total_query)
            total_sensors = total_result.scalar()
            
            # Get active sensors
            active_query = select(func.count(Sensor.id)).where(Sensor.is_active == True)
            active_result = await session.execute(active_query)
            active_sensors = active_result.scalar()
            
            # Get offline sensors
            offline_query = select(func.count(Sensor.id)).where(Sensor.status == SensorStatus.OFFLINE)
            offline_result = await session.execute(offline_query)
            offline_sensors = offline_result.scalar()
            
            # Get sensors due for maintenance (simplified logic)
            maintenance_due_query = select(func.count(Sensor.id)).where(
                and_(
                    Sensor.next_maintenance_due <= datetime.utcnow(),
                    Sensor.is_active == True
                )
            )
            maintenance_due_result = await session.execute(maintenance_due_query)
            maintenance_due = maintenance_due_result.scalar()
            
            # Get sensors with low battery
            low_battery_query = select(func.count(Sensor.id)).where(
                and_(
                    Sensor.battery_level <= Sensor.battery_low_threshold,
                    Sensor.is_active == True
                )
            )
            low_battery_result = await session.execute(low_battery_query)
            low_battery_count = low_battery_result.scalar()
            
            # Get sensors with low signal
            low_signal_query = select(func.count(Sensor.id)).where(
                and_(
                    Sensor.signal_strength <= Sensor.signal_low_threshold,
                    Sensor.is_active == True
                )
            )
            low_signal_result = await session.execute(low_signal_query)
            low_signal_count = low_signal_result.scalar()
            
            return SensorSummary(
                total_sensors=total_sensors,
                active_sensors=active_sensors,
                offline_sensors=offline_sensors,
                maintenance_due=maintenance_due,
                low_battery_count=low_battery_count,
                low_signal_count=low_signal_count,
                last_updated=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error getting sensor summary: {e}")
            raise

    def _convert_to_response(self, sensor: Sensor) -> SensorResponse:
        """Convert Sensor model to SensorResponse"""
        return SensorResponse(
            id=sensor.id,
            sensor_id=sensor.sensor_id,
            name=sensor.name,
            description=sensor.description,
            sensor_type=sensor.sensor_type,
            location_lat=sensor.location_lat,
            location_lng=sensor.location_lng,
            location_description=sensor.location_description,
            battery_level=sensor.battery_level,
            signal_strength=sensor.signal_strength,
            status=sensor.status,
            is_active=sensor.is_active,
            installation_date=sensor.installation_date,
            last_maintenance=sensor.last_maintenance,
            last_reading_time=sensor.last_reading_time,
            next_maintenance_due=sensor.next_maintenance_due,
            reading_interval_minutes=sensor.reading_interval_minutes,
            battery_low_threshold=sensor.battery_low_threshold,
            signal_low_threshold=sensor.signal_low_threshold,
            created_at=sensor.created_at,
            updated_at=sensor.updated_at
        )

    def _convert_health_to_response(self, health: SensorHealth) -> SensorHealthResponse:
        """Convert SensorHealth model to SensorHealthResponse"""
        return SensorHealthResponse(
            id=health.id,
            sensor_id=health.sensor_id,
            battery_level=health.battery_level,
            signal_strength=health.signal_strength,
            status=health.status,
            temperature_celsius=health.temperature_celsius,
            humidity_percent=health.humidity_percent,
            recorded_at=health.recorded_at,
            notes=health.notes
        )
