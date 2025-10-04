from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_session
from app.models.user import User
from app.models.sensor_data import (
    Sensor, SensorHealth, SensorCreate, SensorUpdate, SensorResponse, 
    SensorHealthResponse, SensorSummary, SensorStatus
)
from app.core.dependencies import get_current_admin_user
from app.services.sensor_service import SensorService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sensors", tags=["Admin - Sensor Management"])

@router.get("/", response_model=List[SensorResponse])
async def list_all_sensors(
    status_filter: Optional[SensorStatus] = Query(None, description="Filter by sensor status"),
    active_only: bool = Query(True, description="Show only active sensors"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    List all sensors with current status and location.
    Admin-only endpoint for sensor management dashboard.
    """
    try:
        sensors = await sensor_service.get_all_sensors(
            session=session,
            status_filter=status_filter,
            active_only=active_only
        )
        return sensors
    except Exception as e:
        logger.error(f"Error listing sensors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor list"
        )

@router.get("/summary", response_model=SensorSummary)
async def get_sensor_summary(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Get sensor summary statistics for admin dashboard.
    """
    try:
        summary = await sensor_service.get_sensor_summary(session)
        return summary
    except Exception as e:
        logger.error(f"Error getting sensor summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor summary"
        )

@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor_details(
    sensor_id: str,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Get detailed information for a specific sensor.
    """
    try:
        sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        return sensor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor details"
        )

@router.get("/{sensor_id}/health", response_model=List[SensorHealthResponse])
async def get_sensor_health_history(
    sensor_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (1-168)"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Get historical health logs for a specific sensor.
    Used for generating health charts and trend analysis.
    """
    try:
        # Verify sensor exists
        sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Get health history
        since = datetime.utcnow() - timedelta(hours=hours)
        health_logs = await sensor_service.get_sensor_health_history(
            sensor_id, session, since=since
        )
        return health_logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health history for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor health history"
        )

@router.post("/register", response_model=SensorResponse)
async def register_new_sensor(
    sensor_data: SensorCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Register a new sensor device.
    Admin-only endpoint for adding new sensors to the system.
    """
    try:
        # Check if sensor_id already exists
        existing_sensor = await sensor_service.get_sensor_by_id(sensor_data.sensor_id, session)
        if existing_sensor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sensor with ID {sensor_data.sensor_id} already exists"
            )
        
        # Create new sensor
        new_sensor = await sensor_service.create_sensor(sensor_data, session)
        logger.info(f"Admin {current_user.username} registered new sensor {sensor_data.sensor_id}")
        return new_sensor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering sensor {sensor_data.sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register sensor"
        )

@router.put("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: str,
    sensor_update: SensorUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Update sensor configuration and metadata.
    """
    try:
        # Verify sensor exists
        existing_sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not existing_sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Update sensor
        updated_sensor = await sensor_service.update_sensor(sensor_id, sensor_update, session)
        logger.info(f"Admin {current_user.username} updated sensor {sensor_id}")
        return updated_sensor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update sensor"
        )

@router.delete("/{sensor_id}")
async def deactivate_sensor(
    sensor_id: str,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Deactivate a sensor (soft delete).
    """
    try:
        # Verify sensor exists
        existing_sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not existing_sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Deactivate sensor
        await sensor_service.deactivate_sensor(sensor_id, session)
        logger.info(f"Admin {current_user.username} deactivated sensor {sensor_id}")
        return {"message": f"Sensor {sensor_id} has been deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate sensor"
        )

@router.post("/{sensor_id}/maintenance")
async def record_maintenance(
    sensor_id: str,
    maintenance_notes: str = Query(..., description="Maintenance notes"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Record maintenance performed on a sensor.
    """
    try:
        # Verify sensor exists
        existing_sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not existing_sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Record maintenance
        await sensor_service.record_maintenance(sensor_id, maintenance_notes, session)
        logger.info(f"Admin {current_user.username} recorded maintenance for sensor {sensor_id}")
        return {"message": f"Maintenance recorded for sensor {sensor_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording maintenance for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record maintenance"
        )

@router.get("/{sensor_id}/readings")
async def get_sensor_readings(
    sensor_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of readings to retrieve (1-168)"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    sensor_service: SensorService = Depends(SensorService)
):
    """
    Get recent sensor readings for analysis.
    """
    try:
        # Verify sensor exists
        sensor = await sensor_service.get_sensor_by_id(sensor_id, session)
        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sensor {sensor_id} not found"
            )
        
        # Get readings
        since = datetime.utcnow() - timedelta(hours=hours)
        readings = await sensor_service.get_sensor_readings(sensor_id, session, since=since)
        return readings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting readings for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sensor readings"
        )
