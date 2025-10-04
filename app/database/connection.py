from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.engine.url import make_url
import asyncio


# Create async engine
database_url = settings.database_url
url = make_url(database_url)

engine_kwargs = {
    "echo": settings.debug,
    "future": True,
}

# If using psycopg driver, enable async_fallback to avoid Proactor loop issues on Windows
if "+psycopg" in url.drivername:
    engine_kwargs["connect_args"] = {"async_fallback": True}

engine = create_async_engine(database_url, **engine_kwargs)

# Create async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    """Dependency to get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables"""
    # Try to enable PostGIS extension in a separate transaction
    if "postgresql" in database_url:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                print("PostGIS extension enabled successfully")
        except Exception as e:
            print(f"Warning: Could not enable PostGIS extension: {e}")
            print("Continuing without PostGIS - geometry columns will be created as text")
    
    # Create tables in a separate transaction
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
