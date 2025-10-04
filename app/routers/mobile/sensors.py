from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.flood_service import FloodService
from app.models.sensor_data import Sensor, SensorResponse
from app.models.flood_data import FloodReading
from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/api/mobile/sensors", tags=["mobile-sensors"])


@router.post("/data", response_model=Dict[str, Any])
async def submit_sensor_data(
    sensor_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Submit sensor data from mobile device - Legacy endpoint.
    New sensor data should use /api/mobile/sensor-data/ingest
    """
    return {
        "success": True,
        "message": "Legacy endpoint - please use /api/mobile/sensor-data/ingest for new sensor data",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/data", response_model=List[Dict[str, Any]])
async def get_user_sensor_data(
    limit: int = Query(50, description="Number of records to return"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get recent flood readings for mobile display.
    Mobile-optimized with limited fields.
    """
    recent_readings = await flood_service.get_recent_readings(session, limit=limit)
    
    # Format for mobile
    mobile_data = []
    for reading in recent_readings:
        mobile_data.append({
            "id": reading.id,
            "water_level_cm": reading.water_level_cm,
            "rainfall_mm": reading.rainfall_mm,
            "risk_level": reading.risk_level.value,
            "location": {
                "lat": reading.location_lat,
                "lng": reading.location_lng
            },
            "sensor_id": reading.sensor_id,
            "timestamp": reading.timestamp,
            "notes": reading.notes
        })
    
    return mobile_data


@router.get("/latest/{sensor_id}", response_model=Dict[str, Any])
async def get_latest_sensor_reading(
    sensor_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get the latest reading for a specific sensor.
    """
    latest_reading = await flood_service.get_latest_sensor_reading(sensor_id, session)
    
    if not latest_reading:
        raise HTTPException(status_code=404, detail="No data found for this sensor")
    
    return {
        "sensor_id": latest_reading.sensor_id,
        "water_level_cm": latest_reading.water_level_cm,
        "rainfall_mm": latest_reading.rainfall_mm,
        "risk_level": latest_reading.risk_level.value,
        "location": {
            "lat": latest_reading.location_lat,
            "lng": latest_reading.location_lng
        },
        "timestamp": latest_reading.timestamp,
        "notes": latest_reading.notes
    }
