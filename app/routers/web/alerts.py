from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.flood_service import FloodService
from app.models.flood_data import FloodReading, RiskLevel
from app.core.dependencies import get_current_admin_user
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/api/web/alerts", tags=["web-alerts"])


@router.get("/", response_model=List[FloodReading])
async def get_web_alerts(
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, description="Number of records to return"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get flood alerts with advanced filtering for web dashboard.
    Admin-only endpoint with comprehensive alert management.
    """
    if risk_level:
        alerts = await flood_service.get_alerts_by_risk_level(risk_level, session)
    else:
        alerts = await flood_service.get_active_alerts(session)
    
    # Web-specific filtering
    if sensor_id:
        alerts = [a for a in alerts if a.sensor_id == sensor_id]
    
    if start_date:
        alerts = [a for a in alerts if a.timestamp >= start_date]
    
    if end_date:
        alerts = [a for a in alerts if a.timestamp <= end_date]
    
    # Limit results
    return alerts[:limit]


@router.get("/analytics", response_model=Dict[str, Any])
async def get_alert_analytics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Get comprehensive alert analytics for web dashboard.
    """
    # Get recent alerts
    recent_alerts = await flood_service.get_recent_alerts(session, days * 24)
    all_alerts = await flood_service.get_active_alerts(session)
    
    # Calculate analytics
    total_alerts = len(all_alerts)
    recent_count = len(recent_alerts)
    
    # Risk level distribution
    risk_distribution = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for alert in all_alerts:
        risk_distribution[alert.risk_level] += 1
    
    # Recent alerts by day
    daily_counts = {}
    for alert in recent_alerts:
        date_key = alert.timestamp.date().isoformat()
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
    
    # Top sensors by alert count
    sensor_counts = {}
    for alert in all_alerts:
        sensor_counts[alert.sensor_id] = sensor_counts.get(alert.sensor_id, 0) + 1
    
    top_sensors = sorted(sensor_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_alerts": total_alerts,
        "recent_alerts": recent_count,
        "risk_distribution": risk_distribution,
        "daily_counts": daily_counts,
        "top_sensors": [{"sensor_id": sensor, "alert_count": count} for sensor, count in top_sensors],
        "analysis_period_days": days
    }


@router.get("/export")
async def export_alerts(
    format: str = Query("json", description="Export format (json, csv)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    flood_service: FloodService = Depends(lambda: FloodService())
):
    """
    Export alerts data for analysis.
    """
    if risk_level:
        alerts = await flood_service.get_alerts_by_risk_level(risk_level, session)
    else:
        alerts = await flood_service.get_active_alerts(session)
    
    # Apply date filters
    if start_date:
        alerts = [a for a in alerts if a.timestamp >= start_date]
    if end_date:
        alerts = [a for a in alerts if a.timestamp <= end_date]
    
    if format == "json":
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "sensor_id": alert.sensor_id,
                    "risk_level": alert.risk_level,
                    "water_level_cm": alert.water_level_cm,
                    "rainfall_mm": alert.rainfall_mm,
                    "location_lat": alert.location_lat,
                    "location_lng": alert.location_lng,
                    "timestamp": alert.timestamp,
                    "notes": alert.notes
                }
                for alert in alerts
            ],
            "export_info": {
                "total_records": len(alerts),
                "exported_at": datetime.utcnow(),
                "exported_by": current_user.username
            }
        }
    else:
        # CSV format would be implemented here
        raise HTTPException(status_code=400, detail="CSV export not yet implemented")


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Acknowledge an alert (web admin feature).
    In a real implementation, this would update the alert status.
    """
    # This would typically update an alert status field
    # For now, we'll just return a success message
    return {
        "message": f"Alert {alert_id} acknowledged by {current_user.username}",
        "acknowledged_at": datetime.utcnow(),
        "acknowledged_by": current_user.username
    }
