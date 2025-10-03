from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_session
from app.models.user import User
from app.models.sensor_data import SensorData, SensorDataRead
from app.core.dependencies import get_current_user
from app.schemas.sensor_data import SensorDataCreate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/current", response_model=dict)
async def get_current_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current flood alerts based on latest sensor data"""
    # Get latest sensor data from all sensors
    result = await session.execute(
        select(SensorData)
        .order_by(desc(SensorData.created_at))
        .limit(10)
    )
    recent_data = result.scalars().all()
    
    # Analyze data for alerts
    alerts = []
    for data in recent_data:
        alert_level = "normal"
        if data.water_level_cm > 50:
            alert_level = "high"
        elif data.water_level_cm > 30:
            alert_level = "medium"
        
        if data.rainfall_mm > 20:
            alert_level = "high" if alert_level == "medium" else "high"
        elif data.rainfall_mm > 10:
            alert_level = "medium" if alert_level == "normal" else alert_level
        
        if alert_level != "normal":
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
                "timestamp": data.created_at,
                "message": f"Flood alert: {alert_level} water level ({data.water_level_cm}cm) and rainfall ({data.rainfall_mm}mm)"
            })
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "user_role": current_user.role,
        "timestamp": "2024-01-01T00:00:00Z"  # This would be current timestamp
    }


@router.get("/history", response_model=List[SensorDataRead])
async def get_alert_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get historical sensor data for alert analysis"""
    result = await session.execute(
        select(SensorData)
        .order_by(desc(SensorData.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/sensor-data", response_model=dict)
async def submit_sensor_data(
    sensor_data: SensorDataCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit new sensor data (protected endpoint)"""
    db_sensor_data = SensorData(
        **sensor_data.model_dump(),
        user_id=current_user.id
    )
    
    session.add(db_sensor_data)
    await session.commit()
    await session.refresh(db_sensor_data)
    
    # Print to console as requested
    print(f"Sensor data received: {sensor_data.model_dump()}")
    
    return {
        "message": "Sensor data received and validated",
        "data_id": db_sensor_data.id,
        "received": sensor_data.model_dump()
    }
