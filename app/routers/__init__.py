from .auth import router as auth_router
from .alerts import router as alerts_router
from .sensors import router as sensors_router
from .dashboard import router as dashboard_router
# Map router moved to app/routers/map/data.py
from .report import router as report_router
from .settings import router as settings_router

__all__ = ["auth_router", "alerts_router", "sensors_router", "dashboard_router", "report_router", "settings_router"]
