from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_session
from app.models.user import User
from app.models.sensor_data import Sensor, SensorResponse
from app.models.flood_data import FloodReading
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/data", response_model=dict)
async def submit_sensor_data(
    sensor_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit sensor data (protected endpoint) - Legacy endpoint"""
    # This is a legacy endpoint. New sensor data should use /api/mobile/sensor-data/ingest
    # Print to console as requested
    print(f"Legacy sensor data received: {sensor_data}")
    
    return {
        "message": "Legacy endpoint - please use /api/mobile/sensor-data/ingest for new sensor data",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/data", response_model=List[dict])
async def get_sensor_data(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get sensor data history"""
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(limit)
    )
    readings = result.scalars().all()
    
    # Convert to dict format for response
    return [
        {
            "id": reading.id,
            "sensor_id": reading.sensor_id,
            "water_level_cm": reading.water_level_cm,
            "rainfall_mm": reading.rainfall_mm,
            "risk_level": reading.risk_level.value,
            "timestamp": reading.timestamp,
            "location_lat": reading.location_lat,
            "location_lng": reading.location_lng,
            "notes": reading.notes
        }
        for reading in readings
    ]


@router.get("/data/latest", response_model=dict)
async def get_latest_sensor_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get latest sensor data"""
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(1)
    )
    latest_data = result.scalar_one_or_none()
    
    if not latest_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensor data found"
        )
    
    return {
        "id": latest_data.id,
        "sensor_id": latest_data.sensor_id,
        "water_level_cm": latest_data.water_level_cm,
        "rainfall_mm": latest_data.rainfall_mm,
        "risk_level": latest_data.risk_level.value,
        "timestamp": latest_data.timestamp,
        "location_lat": latest_data.location_lat,
        "location_lng": latest_data.location_lng,
        "notes": latest_data.notes
    }
