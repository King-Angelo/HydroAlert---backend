from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.flood_service import FloodService
from app.models.sensor_data import Sensor, SensorResponse
from app.models.flood_data import FloodReading
from app.core.dependencies import get_current_admin_user
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/api/web/sensors", tags=["web-sensors"])


@router.get("/data", response_model=List[dict])
async def get_all_sensor_data(
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    limit: int = Query(100, description="Number of records to return"),
    offset: int = Query(0, description="Number of records to skip"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get all flood readings with admin-level filtering and pagination.
    """
    # Get recent flood readings
    recent_readings = await flood_service.get_recent_readings(session, limit=limit)
    
    # Filter by sensor_id if provided
    if sensor_id:
        recent_readings = [reading for reading in recent_readings if reading.sensor_id == sensor_id]
    
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
        for reading in recent_readings
    ]


@router.get("/analytics", response_model=Dict[str, Any])
async def get_sensor_analytics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get comprehensive sensor analytics for web dashboard.
    """
    from datetime import datetime, timedelta
    
    # Get recent flood readings
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    all_readings = await flood_service.get_recent_readings(session, limit=1000)
    recent_readings = [reading for reading in all_readings if reading.timestamp >= cutoff_time]
    
    # Calculate analytics
    total_readings = len(all_readings)
    recent_count = len(recent_readings)
    
    # Average water levels
    if recent_readings:
        avg_water_level = sum(reading.water_level_cm for reading in recent_readings) / len(recent_readings)
        avg_rainfall = sum(reading.rainfall_mm for reading in recent_readings) / len(recent_readings)
        max_water_level = max(reading.water_level_cm for reading in recent_readings)
        max_rainfall = max(reading.rainfall_mm for reading in recent_readings)
    else:
        avg_water_level = avg_rainfall = max_water_level = max_rainfall = 0
    
    # Sensor activity
    sensor_activity = {}
    for reading in recent_readings:
        sensor_id = reading.sensor_id or "unknown"
        sensor_activity[sensor_id] = sensor_activity.get(sensor_id, 0) + 1
    
    top_sensors = sorted(sensor_activity.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Daily readings
    daily_counts = {}
    for reading in recent_readings:
        date_key = reading.timestamp.date().isoformat()
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
    
    return {
        "total_readings": total_readings,
        "recent_readings": recent_count,
        "analysis_period_days": days,
        "averages": {
            "water_level_cm": round(avg_water_level, 2),
            "rainfall_mm": round(avg_rainfall, 2)
        },
        "maximums": {
            "water_level_cm": max_water_level,
            "rainfall_mm": max_rainfall
        },
        "top_active_sensors": [{"sensor_id": sensor, "reading_count": count} for sensor, count in top_sensors],
        "daily_reading_counts": daily_counts
    }


@router.post("/data/bulk", response_model=Dict[str, Any])
async def bulk_import_sensor_data(
    sensor_data_list: List[dict],
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Bulk import sensor data (admin feature) - Legacy endpoint.
    """
    return {
        "message": "Legacy endpoint - please use /api/mobile/sensor-data/ingest for new sensor data",
        "imported_count": 0,
        "alert_count": 0,
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.delete("/data/{data_id}")
async def delete_sensor_data(
    data_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete flood reading (admin feature).
    """
    from sqlalchemy import select
    from app.models.flood_data import FloodReading
    
    # Get the reading
    result = await session.execute(select(FloodReading).where(FloodReading.id == data_id))
    reading = result.scalar_one_or_none()
    
    if not reading:
        raise HTTPException(status_code=404, detail="Flood reading not found")
    
    # Delete the reading
    await session.delete(reading)
    await session.commit()
    
    return {
        "success": True,
        "message": f"Flood reading {data_id} deleted successfully",
        "deleted_by": current_user.username
    }
