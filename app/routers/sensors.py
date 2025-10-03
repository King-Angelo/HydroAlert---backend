from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_session
from app.models.user import User
from app.models.sensor_data import SensorData, SensorDataRead
from app.core.dependencies import get_current_user
from app.schemas.sensor_data import SensorDataCreate

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/data", response_model=dict)
async def submit_sensor_data(
    sensor_data: SensorDataCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit sensor data (protected endpoint)"""
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


@router.get("/data", response_model=List[SensorDataRead])
async def get_sensor_data(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get sensor data history"""
    result = await session.execute(
        select(SensorData)
        .order_by(desc(SensorData.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/data/latest", response_model=SensorDataRead)
async def get_latest_sensor_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get latest sensor data"""
    result = await session.execute(
        select(SensorData)
        .order_by(desc(SensorData.created_at))
        .limit(1)
    )
    latest_data = result.scalar_one_or_none()
    
    if not latest_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensor data found"
        )
    
    return latest_data
