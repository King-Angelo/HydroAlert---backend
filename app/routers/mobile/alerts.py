from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.flood_service import FloodService
from app.models.flood_data import FloodReading
from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.user import User
# math import removed - no longer needed with PostGIS

router = APIRouter(prefix="/api/mobile/alerts", tags=["mobile-alerts"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_mobile_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get flood alerts optimized for mobile consumption.
    Returns simplified alert data with essential information only.
    """
    alerts = await flood_service.get_active_alerts(session)
    
    # Mobile-specific filtering/formatting
    mobile_alerts = []
    for alert in alerts:
        mobile_alerts.append({
            "id": alert.id,
            "sensor_id": alert.sensor_id,
            "risk_level": alert.risk_level,
            "water_level_cm": alert.water_level_cm,
            "rainfall_mm": alert.rainfall_mm,
            "location": {
                "lat": alert.location_lat,
                "lng": alert.location_lng
            },
            "timestamp": alert.timestamp,
            "notes": alert.notes
        })
    
    return mobile_alerts


@router.get("/nearby", response_model=List[Dict[str, Any]])
async def get_nearby_alerts(
    latitude: float = Query(..., description="User's latitude"),
    longitude: float = Query(..., description="User's longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get alerts within a specific radius of user's location.
    Mobile-specific feature for location-based alerts.
    """
    # Use PostGIS for efficient proximity search
    nearby_alerts = await flood_service.get_alerts_by_location(latitude, longitude, session, radius_km)
    
    # Format response
    formatted_alerts = []
    for alert in nearby_alerts:
        formatted_alerts.append({
            "id": alert.id,
            "sensor_id": alert.sensor_id,
            "risk_level": alert.risk_level,
            "water_level_cm": alert.water_level_cm,
            "rainfall_mm": alert.rainfall_mm,
            "location": {
                "lat": alert.location_lat,
                "lng": alert.location_lng
            },
            "timestamp": alert.timestamp,
            "notes": alert.notes
        })
    
    return formatted_alerts


@router.get("/summary", response_model=Dict[str, Any])
async def get_alerts_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get a summary of alerts for mobile dashboard.
    """
    alerts = await flood_service.get_active_alerts(session)
    
    # Count by risk level
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for alert in alerts:
        risk_counts[alert.risk_level] += 1
    
    return {
        "total_alerts": len(alerts),
        "risk_levels": risk_counts,
        "latest_alert": alerts[0].timestamp if alerts else None,
        "has_critical": risk_counts["CRITICAL"] > 0
    }


# Haversine function removed - now using PostGIS for efficient geospatial queries
