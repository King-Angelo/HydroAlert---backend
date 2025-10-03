from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime
from app.database import get_session
from app.models.user import User
from app.models.map_data import (
    EvacuationCenter, 
    CenterStatus, 
    calculate_occupancy_percentage,
    determine_center_status
)
from app.schemas.map import (
    EvacuationCenterResponse,
    EvacuationCenterListResponse,
    EvacuationCenterCreateResponse,
    OccupancyUpdateResponse,
    CenterLocation,
    MapDataResponse,
    CenterCapacityInfo,
    CapacitySummaryResponse
)
from app.core.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/centers", response_model=EvacuationCenterListResponse)
async def get_evacuation_centers(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all evacuation centers with their current status and capacity information.
    Protected endpoint requiring JWT authentication.
    """
    # Get all evacuation centers
    result = await session.execute(select(EvacuationCenter))
    centers = result.scalars().all()
    
    # Transform to response format
    center_responses = []
    total_capacity = 0
    total_occupancy = 0
    open_centers = 0
    full_centers = 0
    
    for center in centers:
        available_capacity = center.max_capacity - center.current_occupancy
        occupancy_percentage = calculate_occupancy_percentage(center.current_occupancy, center.max_capacity)
        is_available = center.status in [CenterStatus.OPEN, CenterStatus.CLOSING] and available_capacity > 0
        
        center_response = EvacuationCenterResponse(
            **center.model_dump(),
            occupancy_percentage=occupancy_percentage,
            available_capacity=available_capacity,
            is_available=is_available
        )
        center_responses.append(center_response)
        
        # Update totals
        total_capacity += center.max_capacity
        total_occupancy += center.current_occupancy
        
        if center.status == CenterStatus.OPEN:
            open_centers += 1
        elif center.status == CenterStatus.FULL:
            full_centers += 1
    
    return EvacuationCenterListResponse(
        centers=center_responses,
        total_centers=len(centers),
        open_centers=open_centers,
        full_centers=full_centers,
        total_capacity=total_capacity,
        total_occupancy=total_occupancy
    )


@router.post("/centers", response_model=EvacuationCenterCreateResponse)
async def create_evacuation_center(
    center_data: EvacuationCenter,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new evacuation center.
    Admin only endpoint.
    """
    # Validate that occupancy doesn't exceed capacity
    if center_data.current_occupancy > center_data.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current occupancy cannot exceed maximum capacity"
        )
    
    # Create new center
    db_center = EvacuationCenter(
        **center_data.model_dump(),
        updated_at=datetime.utcnow()
    )
    
    session.add(db_center)
    await session.commit()
    await session.refresh(db_center)
    
    # Create response
    available_capacity = db_center.max_capacity - db_center.current_occupancy
    occupancy_percentage = calculate_occupancy_percentage(db_center.current_occupancy, db_center.max_capacity)
    is_available = db_center.status in [CenterStatus.OPEN, CenterStatus.CLOSING] and available_capacity > 0
    
    center_response = EvacuationCenterResponse(
        **db_center.model_dump(),
        occupancy_percentage=occupancy_percentage,
        available_capacity=available_capacity,
        is_available=is_available
    )
    
    return EvacuationCenterCreateResponse(
        message="Evacuation center created successfully",
        center_id=db_center.id,
        center=center_response
    )


@router.put("/centers/{center_id}/occupancy", response_model=OccupancyUpdateResponse)
async def update_center_occupancy(
    center_id: int,
    occupancy_data: OccupancyUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update the current occupancy of a specific evacuation center.
    Admin only endpoint with validation.
    """
    # Get the center
    result = await session.execute(
        select(EvacuationCenter).where(EvacuationCenter.id == center_id)
    )
    center = result.scalar_one_or_none()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evacuation center not found"
        )
    
    # Validate occupancy doesn't exceed capacity
    if occupancy_data.current_occupancy > center.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Occupancy ({occupancy_data.current_occupancy}) cannot exceed maximum capacity ({center.max_capacity})"
        )
    
    # Store previous values
    previous_occupancy = center.current_occupancy
    
    # Update occupancy
    center.current_occupancy = occupancy_data.current_occupancy
    center.updated_at = datetime.utcnow()
    
    # Auto-determine status if not provided
    if occupancy_data.status:
        center.status = occupancy_data.status
    else:
        center.status = determine_center_status(
            center.current_occupancy, 
            center.max_capacity, 
            center.status
        )
    
    await session.commit()
    await session.refresh(center)
    
    # Calculate response values
    occupancy_percentage = calculate_occupancy_percentage(center.current_occupancy, center.max_capacity)
    available_capacity = center.max_capacity - center.current_occupancy
    
    return OccupancyUpdateResponse(
        message="Occupancy updated successfully",
        center_id=center.id,
        previous_occupancy=previous_occupancy,
        new_occupancy=center.current_occupancy,
        occupancy_percentage=occupancy_percentage,
        status=center.status,
        available_capacity=available_capacity
    )


@router.get("/centers/locations", response_model=MapDataResponse)
async def get_center_locations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get evacuation center locations for map display.
    Optimized for RouteMap.tsx component.
    """
    result = await session.execute(select(EvacuationCenter))
    centers = result.scalars().all()
    
    center_locations = []
    for center in centers:
        available_capacity = center.max_capacity - center.current_occupancy
        occupancy_percentage = calculate_occupancy_percentage(center.current_occupancy, center.max_capacity)
        
        center_location = CenterLocation(
            id=center.id,
            name=center.name,
            latitude=center.latitude,
            longitude=center.longitude,
            status=center.status,
            occupancy_percentage=occupancy_percentage,
            available_capacity=available_capacity
        )
        center_locations.append(center_location)
    
    return MapDataResponse(
        centers=center_locations,
        flood_zones=None,  # Placeholder for future flood zone data
        last_updated=datetime.utcnow()
    )


@router.get("/centers/capacity-summary", response_model=CapacitySummaryResponse)
async def get_capacity_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get capacity summary for all evacuation centers.
    Useful for dashboard displays.
    """
    result = await session.execute(select(EvacuationCenter))
    centers = result.scalars().all()
    
    center_capacities = []
    total_capacity = 0
    total_occupancy = 0
    
    for center in centers:
        available_capacity = center.max_capacity - center.current_occupancy
        occupancy_percentage = calculate_occupancy_percentage(center.current_occupancy, center.max_capacity)
        
        center_capacity = CenterCapacityInfo(
            center_id=center.id,
            name=center.name,
            max_capacity=center.max_capacity,
            current_occupancy=center.current_occupancy,
            available_capacity=available_capacity,
            occupancy_percentage=occupancy_percentage,
            status=center.status
        )
        center_capacities.append(center_capacity)
        
        total_capacity += center.max_capacity
        total_occupancy += center.current_occupancy
    
    overall_occupancy_percentage = calculate_occupancy_percentage(total_occupancy, total_capacity) if total_capacity > 0 else 0.0
    
    return CapacitySummaryResponse(
        centers=center_capacities,
        total_capacity=total_capacity,
        total_occupancy=total_occupancy,
        total_available=total_capacity - total_occupancy,
        overall_occupancy_percentage=overall_occupancy_percentage
    )


@router.get("/centers/{center_id}", response_model=EvacuationCenterResponse)
async def get_center_details(
    center_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific evacuation center.
    """
    result = await session.execute(
        select(EvacuationCenter).where(EvacuationCenter.id == center_id)
    )
    center = result.scalar_one_or_none()
    
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evacuation center not found"
        )
    
    available_capacity = center.max_capacity - center.current_occupancy
    occupancy_percentage = calculate_occupancy_percentage(center.current_occupancy, center.max_capacity)
    is_available = center.status in [CenterStatus.OPEN, CenterStatus.CLOSING] and available_capacity > 0
    
    return EvacuationCenterResponse(
        **center.model_dump(),
        occupancy_percentage=occupancy_percentage,
        available_capacity=available_capacity,
        is_available=is_available
    )
