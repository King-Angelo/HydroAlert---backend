from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_session
from app.models.user import User
from app.models.flood_data import FloodReading, RiskLevel, calculate_risk_level
from app.schemas.dashboard import (
    DashboardStatusResponse, 
    FloodStatusSummary, 
    DashboardMetrics,
    AlertStatus
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/status", response_model=DashboardStatusResponse)
async def get_dashboard_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current flood status for dashboard display.
    Returns the latest flood reading and overall status assessment.
    """
    # Get the latest flood reading
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(1)
    )
    latest_reading = result.scalar_one_or_none()
    
    if not latest_reading:
        return DashboardStatusResponse(
            overall_status="NO_DATA",
            risk_level=RiskLevel.LOW,
            latest_reading=None,
            last_updated=None,
            alert_active=False,
            message="No flood data available"
        )
    
    # Determine overall status based on risk level
    overall_status = _get_overall_status(latest_reading.risk_level)
    
    # Check if alert should be active
    alert_active = latest_reading.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    # Generate status message
    status_message = _generate_status_message(latest_reading)
    
    return DashboardStatusResponse(
        overall_status=overall_status,
        risk_level=latest_reading.risk_level,
        latest_reading=latest_reading,
        last_updated=latest_reading.timestamp,
        alert_active=alert_active,
        message=status_message
    )


@router.get("/summary", response_model=FloodStatusSummary)
async def get_flood_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a concise flood status summary for dashboard widgets.
    """
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(1)
    )
    latest_reading = result.scalar_one_or_none()
    
    if not latest_reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No flood data available"
        )
    
    location = None
    if latest_reading.location_lat and latest_reading.location_lng:
        location = {
            "lat": latest_reading.location_lat,
            "lng": latest_reading.location_lng
        }
    
    return FloodStatusSummary(
        current_risk=latest_reading.risk_level,
        water_level_cm=latest_reading.water_level_cm,
        rainfall_mm=latest_reading.rainfall_mm,
        sensor_id=latest_reading.sensor_id,
        location=location,
        timestamp=latest_reading.timestamp,
        status_message=_generate_status_message(latest_reading)
    )


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get dashboard metrics and statistics for the last 24 hours.
    """
    # Calculate 24 hours ago
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    
    # Get total readings count
    total_result = await session.execute(
        select(func.count(FloodReading.id))
    )
    total_readings = total_result.scalar() or 0
    
    # Get average water level and rainfall
    avg_result = await session.execute(
        select(
            func.avg(FloodReading.water_level_cm).label('avg_water'),
            func.avg(FloodReading.rainfall_mm).label('avg_rainfall')
        )
    )
    avg_data = avg_result.first()
    average_water_level = float(avg_data.avg_water) if avg_data.avg_water else 0.0
    average_rainfall = float(avg_data.avg_rainfall) if avg_data.avg_rainfall else 0.0
    
    # Get risk level counts
    risk_counts = await session.execute(
        select(
            FloodReading.risk_level,
            func.count(FloodReading.id).label('count')
        )
        .group_by(FloodReading.risk_level)
    )
    
    risk_counts_dict = {row.risk_level: row.count for row in risk_counts}
    
    # Get last 24 hours readings count
    last_24h_result = await session.execute(
        select(func.count(FloodReading.id))
        .where(FloodReading.timestamp >= twenty_four_hours_ago)
    )
    last_24h_readings = last_24h_result.scalar() or 0
    
    return DashboardMetrics(
        total_readings=total_readings,
        average_water_level=average_water_level,
        average_rainfall=average_rainfall,
        high_risk_count=risk_counts_dict.get(RiskLevel.HIGH, 0),
        moderate_risk_count=risk_counts_dict.get(RiskLevel.MODERATE, 0),
        low_risk_count=risk_counts_dict.get(RiskLevel.LOW, 0),
        last_24h_readings=last_24h_readings
    )


@router.get("/alert-status", response_model=AlertStatus)
async def get_alert_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current alert status based on latest flood readings.
    """
    result = await session.execute(
        select(FloodReading)
        .order_by(desc(FloodReading.timestamp))
        .limit(1)
    )
    latest_reading = result.scalar_one_or_none()
    
    if not latest_reading:
        return AlertStatus(
            is_active=False,
            message="No flood data available"
        )
    
    is_active = latest_reading.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    if is_active:
        alert_type = "FLOOD_WARNING" if latest_reading.risk_level == RiskLevel.HIGH else "FLOOD_EMERGENCY"
        severity = latest_reading.risk_level.value
        message = _generate_alert_message(latest_reading)
        
        return AlertStatus(
            is_active=True,
            alert_type=alert_type,
            severity=severity,
            message=message,
            issued_at=latest_reading.timestamp,
            expires_at=latest_reading.timestamp + timedelta(hours=6)  # Alerts expire after 6 hours
        )
    
    return AlertStatus(
        is_active=False,
        message="No active alerts"
    )


def _get_overall_status(risk_level: RiskLevel) -> str:
    """Convert risk level to overall status string"""
    status_mapping = {
        RiskLevel.LOW: "SAFE",
        RiskLevel.MODERATE: "CAUTION",
        RiskLevel.HIGH: "WARNING",
        RiskLevel.CRITICAL: "EMERGENCY"
    }
    return status_mapping.get(risk_level, "UNKNOWN")


def _generate_status_message(reading: FloodReading) -> str:
    """Generate human-readable status message"""
    if reading.risk_level == RiskLevel.CRITICAL:
        return f"CRITICAL: Water level at {reading.water_level_cm}cm, {reading.rainfall_mm}mm rainfall. Immediate evacuation recommended."
    elif reading.risk_level == RiskLevel.HIGH:
        return f"HIGH RISK: Water level at {reading.water_level_cm}cm, {reading.rainfall_mm}mm rainfall. Prepare for potential flooding."
    elif reading.risk_level == RiskLevel.MODERATE:
        return f"MODERATE RISK: Water level at {reading.water_level_cm}cm, {reading.rainfall_mm}mm rainfall. Monitor conditions closely."
    else:
        return f"LOW RISK: Water level at {reading.water_level_cm}cm, {reading.rainfall_mm}mm rainfall. Conditions are normal."


def _generate_alert_message(reading: FloodReading) -> str:
    """Generate alert message for high/critical risk levels"""
    if reading.risk_level == RiskLevel.CRITICAL:
        return f"FLOOD EMERGENCY: Critical water levels detected ({reading.water_level_cm}cm). Evacuate immediately if safe to do so."
    else:
        return f"FLOOD WARNING: High water levels detected ({reading.water_level_cm}cm). Take precautionary measures."
