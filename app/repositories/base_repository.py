from typing import TypeVar, Generic, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from app.database import get_session

T = TypeVar('T', bound=SQLModel)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model_class: type[T]):
        self.model_class = model_class
    
    async def create(self, obj: T, session: AsyncSession) -> T:
        """Create a new record"""
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    
    async def get_by_id(self, id: int, session: AsyncSession) -> Optional[T]:
        """Get record by ID"""
        result = await session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, session: AsyncSession, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination"""
        result = await session.execute(
            select(self.model_class).limit(limit).offset(offset)
        )
        return result.scalars().all()
    
    async def update(self, obj: T, session: AsyncSession) -> T:
        """Update an existing record"""
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    
    async def delete(self, id: int, session: AsyncSession) -> bool:
        """Delete a record by ID"""
        obj = await self.get_by_id(id, session)
        if obj:
            await session.delete(obj)
            await session.commit()
            return True
        return False
