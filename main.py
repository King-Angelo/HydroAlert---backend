from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.database import create_tables
from app.routers import auth_router, alerts_router, sensors_router
from app.routers.dashboard import router as dashboard_router
from app.routers.map import router as map_router
from app.routers.report import router as report_router
from app.routers.settings import router as settings_router
from app.routers.websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="Hydro Alert Flood Monitoring System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.websocket_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(sensors_router)
app.include_router(dashboard_router)
app.include_router(map_router)
app.include_router(report_router)
app.include_router(settings_router)
app.include_router(websocket_router)


@app.get("/")
def read_root():
    return {
        "message": "Hydro Alert Backend is running!",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "hydro-alert-api"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )   