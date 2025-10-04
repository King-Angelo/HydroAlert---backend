from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.websocket.websocket_service import websocket_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/websocket", tags=["admin-websocket"])


class EmergencyAlertData(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=1000)
    severity: str = Field(default="HIGH", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    location: Optional[Dict[str, float]] = Field(default=None, description="Optional location with lat/lng")


class SystemNotificationData(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=1000)
    level: str = Field(default="info", pattern="^(info|warning|error|success)$")


class ReportUpdateData(BaseModel):
    report_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=5, max_length=500)


@router.post("/broadcast/emergency-alert")
async def broadcast_emergency_alert(
    alert_data: EmergencyAlertData,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Broadcast emergency alert to all connected users.
    Admin-only endpoint.
    """
    try:
        await websocket_service.broadcast_emergency_alert(alert_data.model_dump())
        
        logger.info(f"Admin {current_user.username} broadcasted emergency alert: {alert_data.title}")
        
        return {
            "message": "Emergency alert broadcasted successfully",
            "alert_title": alert_data.title,
            "severity": alert_data.severity,
            "broadcasted_by": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting emergency alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast emergency alert"
        )


@router.post("/broadcast/system-notification")
async def broadcast_system_notification(
    notification_data: SystemNotificationData,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Broadcast system notification to all connected users.
    Admin-only endpoint.
    """
    try:
        await websocket_service.broadcast_system_notification(notification_data.model_dump())
        
        logger.info(f"Admin {current_user.username} broadcasted system notification: {notification_data.title}")
        
        return {
            "message": "System notification broadcasted successfully",
            "notification_title": notification_data.title,
            "level": notification_data.level,
            "broadcasted_by": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast system notification"
        )


@router.post("/broadcast/report-update")
async def broadcast_report_update(
    update_data: ReportUpdateData,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Broadcast report update to relevant users.
    Admin-only endpoint.
    """
    try:
        await websocket_service.send_admin_message({
            "title": "Report Update",
            "message": update_data.message,
            "report_id": update_data.report_id,
            "updated_by": current_user.username
        })
        
        logger.info(f"Admin {current_user.username} broadcasted report update for report {update_data.report_id}")
        
        return {
            "message": "Report update broadcasted successfully",
            "report_id": update_data.report_id,
            "update_message": update_data.message,
            "broadcasted_by": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting report update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast report update"
        )


@router.get("/connections")
async def get_connection_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get current WebSocket connection statistics.
    Admin-only endpoint.
    """
    try:
        stats = websocket_service.get_connection_stats()
        
        return {
            "message": "Connection statistics retrieved successfully",
            "stats": stats,
            "requested_by": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection statistics"
        )


@router.post("/test-connection")
async def test_websocket_connection(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Test WebSocket connectivity for a specific user or all users.
    Admin-only endpoint.
    """
    try:
        success = await websocket_service.test_connection(user_id)
        
        if success:
            return {
                "message": "WebSocket connection test successful",
                "tested_user_id": user_id,
                "tested_by": current_user.username
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active WebSocket connection found for user {user_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing WebSocket connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test WebSocket connection"
        )
