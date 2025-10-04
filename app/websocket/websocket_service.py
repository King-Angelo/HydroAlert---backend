from typing import Dict, Any, Optional
from app.websocket.connection_manager import connection_manager
from app.websocket.map_events import map_event_broadcaster
from app.models.emergency_report import EmergencyReport
from app.models.flood_data import FloodReading
from app.models.evacuation_center import EvacuationCenter
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class WebSocketService:
    """Service layer for WebSocket operations and real-time notifications"""
    
    def __init__(self):
        self.connection_manager = connection_manager
    
    async def notify_new_report(self, report: EmergencyReport, submitter: User):
        """Notify relevant users about a new emergency report"""
        try:
            # If it's a critical report, notify all admins immediately
            if report.severity in ["HIGH", "CRITICAL"]:
                await self.connection_manager.broadcast_new_critical_report({
                    "id": report.id,
                    "title": report.title,
                    "severity": report.severity,
                    "category": report.category,
                    "location_lat": report.location_lat,
                    "location_lng": report.location_lng
                })
                logger.info(f"Broadcasted new critical report {report.id} to all admins")
            
            # Notify the submitter that their report was received
            await self.connection_manager.send_to_user(submitter.id, {
                "type": "report_submitted",
                "data": {
                    "report_id": report.id,
                    "title": report.title,
                    "status": report.status,
                    "message": "Your emergency report has been submitted and is being reviewed",
                    "timestamp": report.submitted_at.isoformat()
                }
            })
            logger.info(f"Notified user {submitter.username} about submitted report {report.id}")
            
        except Exception as e:
            logger.error(f"Error notifying new report {report.id}: {str(e)}")
    
    async def notify_report_triage_update(self, report: EmergencyReport, triaged_by: User):
        """Notify users about report triage updates"""
        try:
            # Notify the report submitter
            await self.connection_manager.broadcast_report_triaged(
                report.id,
                report.status,
                triaged_by.username,
                report.user_id
            )
            logger.info(f"Broadcasted triage update for report {report.id} by {triaged_by.username}")
            
        except Exception as e:
            logger.error(f"Error notifying triage update for report {report.id}: {str(e)}")
    
    async def broadcast_emergency_alert(self, alert_data: Dict[str, Any]):
        """Broadcast emergency alert to all connected users"""
        try:
            await self.connection_manager.broadcast_emergency_alert(alert_data)
            logger.info(f"Broadcasted emergency alert: {alert_data.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error broadcasting emergency alert: {str(e)}")
    
    async def broadcast_system_notification(self, notification_data: Dict[str, Any]):
        """Broadcast system notification to all connected users"""
        try:
            await self.connection_manager.broadcast_system_notification(notification_data)
            logger.info(f"Broadcasted system notification: {notification_data.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error broadcasting system notification: {str(e)}")
    
    async def send_admin_message(self, message_data: Dict[str, Any]):
        """Send message to all admin connections"""
        try:
            await self.connection_manager.send_to_admins({
                "type": "admin_message",
                "data": message_data
            })
            logger.info(f"Sent admin message: {message_data.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error sending admin message: {str(e)}")
    
    async def notify_user_report_update(self, user_id: int, report_id: int, update_data: Dict[str, Any]):
        """Send specific update to a user about their report"""
        try:
            await self.connection_manager.send_to_user(user_id, {
                "type": "report_update",
                "data": {
                    "report_id": report_id,
                    **update_data
                }
            })
            logger.info(f"Sent report update to user {user_id} for report {report_id}")
            
        except Exception as e:
            logger.error(f"Error notifying user {user_id} about report {report_id}: {str(e)}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current WebSocket connection statistics"""
        return self.connection_manager.get_connection_stats()
    
    async def notify_flood_reading_update(self, reading: FloodReading, action: str = "create"):
        """Notify map clients about flood reading updates"""
        try:
            await map_event_broadcaster.broadcast_flood_reading_update(reading, action)
            logger.info(f"Broadcasted flood reading {action} to map clients")
        except Exception as e:
            logger.error(f"Error broadcasting flood reading update: {str(e)}")
    
    async def notify_emergency_report_map_update(self, report: EmergencyReport, action: str = "create"):
        """Notify map clients about emergency report updates"""
        try:
            await map_event_broadcaster.broadcast_emergency_report_update(report, action)
            logger.info(f"Broadcasted emergency report {action} to map clients")
        except Exception as e:
            logger.error(f"Error broadcasting emergency report map update: {str(e)}")
    
    async def notify_evacuation_center_update(self, center: EvacuationCenter, action: str = "update"):
        """Notify map clients about evacuation center updates"""
        try:
            await map_event_broadcaster.broadcast_evacuation_center_update(center, action)
            logger.info(f"Broadcasted evacuation center {action} to map clients")
        except Exception as e:
            logger.error(f"Error broadcasting evacuation center update: {str(e)}")
    
    def get_map_viewport_stats(self) -> Dict[str, Any]:
        """Get map viewport registration statistics"""
        return map_event_broadcaster.get_viewport_stats()
    
    async def test_connection(self, user_id: Optional[int] = None) -> bool:
        """Test WebSocket connectivity for a specific user or all users"""
        try:
            if user_id:
                # Test specific user connection
                if user_id in self.connection_manager.user_connections:
                    test_message = {
                        "type": "connection_test",
                        "data": {"message": "WebSocket connection test", "timestamp": "now"}
                    }
                    await self.connection_manager.send_to_user(user_id, test_message)
                    return True
                return False
            else:
                # Test all connections
                test_message = {
                    "type": "connection_test",
                    "data": {"message": "WebSocket connection test", "timestamp": "now"}
                }
                await self.connection_manager.send_to_all(test_message)
                return True
                
        except Exception as e:
            logger.error(f"Error testing WebSocket connection: {str(e)}")
            return False

# Global WebSocket service instance
websocket_service = WebSocketService()
