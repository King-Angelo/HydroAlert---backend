from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.database import get_session
from app.models.sensor_data import SensorIngestData, SensorHealthCreate
from app.models.flood_data import FloodReading, RiskLevel, calculate_risk_level
from app.services.sensor_service import SensorService
from app.services.flood_service import FloodService
from app.core.config import settings
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile/sensor-data", tags=["Mobile - Sensor Data"])

def verify_sensor_authentication(sensor_id: str, signature: str, payload: str) -> bool:
    """
    Verify sensor authentication using HMAC signature.
    This provides secure authentication for IoT devices without requiring JWT tokens.
    """
    try:
        # In production, this would use a proper secret key management system
        # For now, we'll use a simple approach with the sensor_id as part of the secret
        secret_key = f"{settings.jwt_secret_key}_{sensor_id}".encode('utf-8')
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret_key,
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying sensor authentication: {e}")
        return False

@router.post("/ingest")
async def ingest_sensor_data(
    sensor_data: SensorIngestData,
    x_sensor_signature: str = Header(..., description="HMAC signature for sensor authentication"),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService),
    flood_service: FloodService = Depends(FloodService)
):
    """
    Secure endpoint for IoT devices to submit sensor readings.
    
    This endpoint performs two critical actions:
    1. Creates a new FloodReading entry with the sensor data
    2. Updates the parent Sensor device's metadata (battery_level, signal_strength, last_reading_time)
    
    Authentication is performed using HMAC signature verification.
    """
    try:
        # Verify sensor authentication
        payload = sensor_data.model_dump_json()
        if not verify_sensor_authentication(sensor_data.sensor_id, x_sensor_signature, payload):
            logger.warning(f"Authentication failed for sensor {sensor_data.sensor_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sensor authentication"
            )
        
        # Verify sensor exists and is active
        sensor = await sensor_service.get_sensor_by_id(sensor_data.sensor_id, session)
        if not sensor:
            logger.warning(f"Unknown sensor {sensor_data.sensor_id} attempted data ingestion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_data.sensor_id} not found"
            )
        
        if not sensor.is_active:
            logger.warning(f"Inactive sensor {sensor_data.sensor_id} attempted data ingestion")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sensor {sensor_data.sensor_id} is not active"
            )
        
        # Calculate risk level based on sensor readings
        risk_level = calculate_risk_level(
            sensor_data.water_level_cm, 
            sensor_data.rainfall_mm
        )
        
        # Create FloodReading entry
        flood_reading = FloodReading(
            sensor_id=sensor_data.sensor_id,
            water_level_cm=sensor_data.water_level_cm,
            rainfall_mm=sensor_data.rainfall_mm,
            risk_level=risk_level,
            location_lat=sensor_data.location_lat,
            location_lng=sensor_data.location_lng,
            timestamp=sensor_data.timestamp or datetime.utcnow(),
            notes=sensor_data.notes
        )
        
        # Save flood reading to database
        created_reading = await flood_service.create_reading(flood_reading, session)
        
        # Update sensor metadata with latest health information
        await sensor_service.update_sensor_health_from_reading(
            sensor_data.sensor_id,
            sensor_data.battery_level,
            sensor_data.signal_strength,
            sensor_data.temperature_celsius,
            sensor_data.humidity_percent,
            session
        )
        
        # Log successful ingestion
        logger.info(
            f"Sensor {sensor_data.sensor_id} data ingested successfully: "
            f"water_level={sensor_data.water_level_cm}cm, "
            f"rainfall={sensor_data.rainfall_mm}mm, "
            f"risk_level={risk_level.value}, "
            f"battery={sensor_data.battery_level}%, "
            f"signal={sensor_data.signal_strength}%"
        )
        
        return {
            "message": "Sensor data ingested successfully",
            "reading_id": created_reading.id,
            "sensor_id": sensor_data.sensor_id,
            "risk_level": risk_level.value,
            "timestamp": created_reading.timestamp.isoformat(),
            "sensor_status": "healthy" if (
                (sensor_data.battery_level is None or sensor_data.battery_level > sensor.battery_low_threshold) and
                (sensor_data.signal_strength is None or sensor_data.signal_strength > sensor.signal_low_threshold)
            ) else "warning"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting sensor data from {sensor_data.sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process sensor data"
        )

@router.get("/health/{sensor_id}")
async def get_sensor_health_status(
    sensor_id: str,
    x_sensor_signature: str = Header(..., description="HMAC signature for sensor authentication"),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Get current health status for a sensor.
    Allows IoT devices to check their current status and configuration.
    """
    try:
        # Verify sensor authentication
        payload = sensor_id
        if not verify_sensor_authentication(sensor_id, x_sensor_signature, payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sensor authentication"
            )
        
        # Get sensor information
        sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Get latest health log
        latest_health = await sensor_service.get_latest_sensor_health(sensor_id, session)
        
        return {
            "sensor_id": sensor_id,
            "status": sensor.status.value,
            "is_active": sensor.is_active,
            "battery_level": sensor.battery_level,
            "signal_strength": sensor.signal_strength,
            "last_reading_time": sensor.last_reading_time.isoformat() if sensor.last_reading_time else None,
            "reading_interval_minutes": sensor.reading_interval_minutes,
            "battery_low_threshold": sensor.battery_low_threshold,
            "signal_low_threshold": sensor.signal_low_threshold,
            "next_maintenance_due": sensor.next_maintenance_due.isoformat() if sensor.next_maintenance_due else None,
            "latest_health": {
                "battery_level": latest_health.battery_level if latest_health else None,
                "signal_strength": latest_health.signal_strength if latest_health else None,
                "status": latest_health.status.value if latest_health else None,
                "recorded_at": latest_health.recorded_at.isoformat() if latest_health else None
            } if latest_health else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health status for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor health status"
        )

@router.post("/health/{sensor_id}")
async def report_sensor_health(
    sensor_id: str,
    health_data: SensorHealthCreate,
    x_sensor_signature: str = Header(..., description="HMAC signature for sensor authentication"),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Allow sensors to report their health status independently of data readings.
    Useful for sensors that need to report health more frequently than data readings.
    """
    try:
        # Verify sensor authentication
        payload = health_data.model_dump_json()
        if not verify_sensor_authentication(sensor_id, x_sensor_signature, payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sensor authentication"
            )
        
        # Verify sensor exists
        sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Create health log entry
        health_log = await sensor_service.create_health_log(health_data, session)
        
        # Update sensor metadata if provided
        if health_data.battery_level is not None or health_data.signal_strength is not None:
            await sensor_service.update_sensor_health_from_reading(
                sensor_id,
                health_data.battery_level,
                health_data.signal_strength,
                health_data.temperature_celsius,
                health_data.humidity_percent,
                session
            )
        
        logger.info(f"Sensor {sensor_id} reported health: battery={health_data.battery_level}%, signal={health_data.signal_strength}%, status={health_data.status.value}")
        
        return {
            "message": "Sensor health reported successfully",
            "health_log_id": health_log.id,
            "sensor_id": sensor_id,
            "recorded_at": health_log.recorded_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting health for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to report sensor health"
        )
