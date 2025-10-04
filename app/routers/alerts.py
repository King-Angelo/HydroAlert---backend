from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_session
from app.models.user import User
from app.models.sensor_data import Sensor, SensorResponse
from app.models.flood_data import FloodReading
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/current", response_model=dict)
async def get_current_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current flood alerts based on latest sensor data"""
    # Get latest flood readings from all sensors
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(10)
    )
    recent_data = result.scalars().all()
    
    # Analyze data for alerts
    alerts = []
    for data in recent_data:
        alert_level = data.risk_level.value.lower()
        
        if alert_level in ["high", "critical"]:
            alerts.append({
                "id": data.id,
                "level": alert_level,
                "water_level_cm": data.water_level_cm,
                "rainfall_mm": data.rainfall_mm,
                "location": {
                    "lat": data.location_lat,
                    "lng": data.location_lng
                } if data.location_lat and data.location_lng else None,
                "sensor_id": data.sensor_id,
                "timestamp": data.timestamp,
                "message": f"Flood alert: {alert_level} water level ({data.water_level_cm}cm) and rainfall ({data.rainfall_mm}mm)"
            })
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "user_role": current_user.role,
        "timestamp": "2024-01-01T00:00:00Z"  # This would be current timestamp
    }


@router.get("/history", response_model=List[dict])
async def get_alert_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get historical sensor data for alert analysis"""
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


@router.post("/sensor-data", response_model=dict)
async def submit_sensor_data(
    sensor_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit new sensor data (protected endpoint) - Legacy endpoint"""
    # This is a legacy endpoint. New sensor data should use /api/mobile/sensor-data/ingest
    # Print to console as requested
    print(f"Legacy sensor data received: {sensor_data}")
    
    return {
        "message": "Legacy endpoint - please use /api/mobile/sensor-data/ingest for new sensor data",
        "timestamp": "2024-01-01T00:00:00Z"
    }
