from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.map_service import MapService
from app.schemas.map import (
    MapBounds, 
    MapDataResponse, 
    EvacuationCenterWithDistance,
    RouteSafetyAssessment
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/map", tags=["map-data"])

@router.get("/data", response_model=MapDataResponse)
async def get_map_data(
    north: float = Query(..., ge=-90, le=90, description="Northern boundary latitude"),
    south: float = Query(..., ge=-90, le=90, description="Southern boundary latitude"),
    east: float = Query(..., ge=-180, le=180, description="Eastern boundary longitude"),
    west: float = Query(..., ge=-180, le=180, description="Western boundary longitude"),
    zoom_level: int = Query(..., ge=1, le=20, description="Map zoom level"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all map data within the specified viewport bounds.
    Returns flood readings, emergency reports, and evacuation centers in GeoJSON format.
    """
    try:
        # Validate bounds
        if north <= south:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="North latitude must be greater than south latitude"
            )
        if east <= west:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="East longitude must be greater than west longitude"
            )
        
        bounds = MapBounds(north=north, south=south, east=east, west=west)
        
        map_service = MapService()
        map_data = await map_service.get_map_data(bounds, zoom_level, session)
        
        logger.info(f"Retrieved map data for user {current_user.username}: {map_data['total_count']} features")
        
        return MapDataResponse(**map_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting map data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve map data"
        )

@router.get("/flood-readings")
async def get_flood_readings_in_bounds(
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get flood readings within the specified bounds.
    Returns flood readings in GeoJSON format.
    """
    try:
        bounds = MapBounds(north=north, south=south, east=east, west=west)
        map_service = MapService()
        
        flood_readings = await map_service._get_flood_readings_in_bounds(bounds, session)
        flood_geojson = [map_service._convert_to_geojson(reading, "flood_readings") for reading in flood_readings]
        
        return {
            "type": "FeatureCollection",
            "features": flood_geojson,
            "total_count": len(flood_geojson),
            "bounds": bounds
        }
        
    except Exception as e:
        logger.error(f"Error getting flood readings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flood readings"
        )

@router.get("/emergency-reports")
async def get_emergency_reports_in_bounds(
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get emergency reports within the specified bounds.
    Returns emergency reports in GeoJSON format.
    """
    try:
        bounds = MapBounds(north=north, south=south, east=east, west=west)
        map_service = MapService()
        
        emergency_reports = await map_service._get_emergency_reports_in_bounds(bounds, session)
        reports_geojson = [map_service._convert_to_geojson(report, "emergency_reports") for report in emergency_reports]
        
        return {
            "type": "FeatureCollection",
            "features": reports_geojson,
            "total_count": len(reports_geojson),
            "bounds": bounds
        }
        
    except Exception as e:
        logger.error(f"Error getting emergency reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency reports"
        )

@router.get("/evacuation-centers")
async def get_evacuation_centers_in_bounds(
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get evacuation centers within the specified bounds.
    Returns evacuation centers in GeoJSON format.
    """
    try:
        bounds = MapBounds(north=north, south=south, east=east, west=west)
        map_service = MapService()
        
        evacuation_centers = await map_service._get_evacuation_centers_in_bounds(bounds, session)
        centers_geojson = [map_service._convert_to_geojson(center, "evacuation_centers") for center in evacuation_centers]
        
        return {
            "type": "FeatureCollection",
            "features": centers_geojson,
            "total_count": len(centers_geojson),
            "bounds": bounds
        }
        
    except Exception as e:
        logger.error(f"Error getting evacuation centers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve evacuation centers"
        )

@router.get("/nearest-evacuation-centers", response_model=List[EvacuationCenterWithDistance])
async def get_nearest_evacuation_centers(
    latitude: float = Query(..., ge=-90, le=90, description="User's current latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="User's current longitude"),
    radius_km: float = Query(10.0, ge=0.1, le=50.0, description="Search radius in kilometers"),
    min_capacity: int = Query(0, ge=0, description="Minimum available capacity required"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Find nearest evacuation centers using PostGIS spatial queries.
    Returns centers sorted by distance with capacity information.
    """
    try:
        map_service = MapService()
        nearest_centers = await map_service.find_nearest_evacuation_centers(
            latitude, longitude, radius_km, min_capacity, session
        )
        
        logger.info(f"Found {len(nearest_centers)} evacuation centers near user {current_user.username}")
        
        return nearest_centers
        
    except Exception as e:
        logger.error(f"Error finding nearest evacuation centers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find nearest evacuation centers"
        )

@router.get("/route-safety", response_model=RouteSafetyAssessment)
async def get_route_safety(
    start_lat: float = Query(..., ge=-90, le=90, description="Start point latitude"),
    start_lng: float = Query(..., ge=-180, le=180, description="Start point longitude"),
    end_lat: float = Query(..., ge=-90, le=90, description="End point latitude"),
    end_lng: float = Query(..., ge=-180, le=180, description="End point longitude"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Calculate route safety considering flood conditions.
    Returns safety assessment with risk level and warnings.
    """
    try:
        map_service = MapService()
        route_safety = await map_service.calculate_route_safety(
            start_lat, start_lng, end_lat, end_lng, session
        )
        
        logger.info(f"Route safety assessment for user {current_user.username}: {route_safety.risk_level}")
        
        return route_safety
        
    except Exception as e:
        logger.error(f"Error calculating route safety: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate route safety"
        )

@router.get("/flood-affected-areas")
async def get_flood_affected_areas(
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get flood affected areas within the specified bounds.
    Returns areas with high flood risk and evacuation center information.
    """
    try:
        bounds = MapBounds(north=north, south=south, east=east, west=west)
        map_service = MapService()
        
        affected_areas = await map_service.get_flood_affected_areas(bounds, session)
        
        logger.info(f"Found {len(affected_areas)} flood affected areas for user {current_user.username}")
        
        return {
            "affected_areas": affected_areas,
            "total_count": len(affected_areas),
            "bounds": bounds
        }
        
    except Exception as e:
        logger.error(f"Error getting flood affected areas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flood affected areas"
        )
