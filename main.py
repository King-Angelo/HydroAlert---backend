from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import sys

from app.core.config import settings
from app.database import create_tables
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.logging import APILoggingMiddleware
from app.core.logging_config import setup_logging
from app.routers import auth_router, alerts_router, sensors_router
from app.routers.dashboard import router as dashboard_router
# Map router moved to app/routers/map/data.py
from app.routers.report import router as report_router
from app.routers.settings import router as settings_router
from app.routers.websocket import map_router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown
    pass


# Windows-specific: ensure psycopg async works with SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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

# API logging middleware (should be first to capture all requests)
app.add_middleware(APILoggingMiddleware)

# Rate limiting middleware
app.add_middleware(
    RateLimitingMiddleware,
    enabled=not settings.debug  # Disable in debug mode for development
)

# Include legacy routers (for backward compatibility)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(sensors_router)
app.include_router(dashboard_router)
# Map router included separately below
app.include_router(report_router)
app.include_router(settings_router)
app.include_router(websocket_router)

# Include client-specific routers
from app.routers.mobile.alerts import router as mobile_alerts_router
from app.routers.mobile.sensors import router as mobile_sensors_router
from app.routers.mobile.reports import router as mobile_reports_router
from app.routers.mobile.sensor_readings import router as mobile_sensor_readings_router
from app.routers.admin.websocket import router as admin_websocket_router
from app.routers.admin.sensors import router as admin_sensors_router
from app.routers.map.data import router as map_data_router
# Map WebSocket router already imported above
from app.routers.web.alerts import router as web_alerts_router
from app.routers.web.sensors import router as web_sensors_router

# Mobile API routes
app.include_router(mobile_alerts_router)
app.include_router(mobile_sensors_router)
app.include_router(mobile_reports_router)
app.include_router(mobile_sensor_readings_router)

# Admin API routes
app.include_router(admin_websocket_router)
app.include_router(admin_sensors_router)

# Map API routes
app.include_router(map_data_router)
# Map WebSocket router included above as websocket_router

# Web API routes
app.include_router(web_alerts_router)
app.include_router(web_sensors_router)


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
        port=8002,
        reload=settings.debug
    )   