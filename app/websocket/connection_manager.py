from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
from app.models.user import User
from app.websocket.auth import websocket_auth
import json
import logging
from datetime import datetime
from app.middleware.logging import ws_logging_middleware

logger = logging.getLogger(__name__)

class AuthenticatedConnectionManager:
    """Enhanced connection manager with authentication and role-based routing"""
    
    def __init__(self):
        self.admin_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}
        self.all_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user: User):
        """Connect authenticated user to appropriate channels"""
        await websocket.accept()
        
        # Add to all connections
        self.all_connections.append(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "connected_at": datetime.utcnow(),
            "channels": await websocket_auth.get_user_channels(user)
        }
        
        # Categorize by role
        if user.role == "admin":
            self.admin_connections.append(websocket)
            logger.info(f"Admin user {user.username} connected to WebSocket")
        else:
            if user.id not in self.user_connections:
                self.user_connections[user.id] = []
            self.user_connections[user.id].append(websocket)
            logger.info(f"User {user.username} connected to WebSocket")
        
        # Log connection event
        ws_logging_middleware.log_connection(
            user_id=user.id,
            endpoint="websocket"
        )
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "data": {
                "message": "WebSocket connection established",
                "user": user.username,
                "role": user.role,
                "channels": self.connection_metadata[websocket]["channels"]
            }
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection from all categories"""
        # Remove from all connections
        if websocket in self.all_connections:
            self.all_connections.remove(websocket)
        
        # Remove from admin connections
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        
        # Remove from user connections
        for user_id, connections in self.user_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                if not connections:  # Remove empty user connection list
                    del self.user_connections[user_id]
                break
        
        # Remove metadata and authentication
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            logger.info(f"User {metadata.get('username', 'unknown')} disconnected from WebSocket")
            
            # Log disconnection event
            ws_logging_middleware.log_disconnection(
                user_id=metadata.get('user_id'),
                endpoint="websocket"
            )
            
            del self.connection_metadata[websocket]
        
        # Remove from authentication manager
        websocket_auth.remove_connection(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                await self.send_personal_message(message, websocket)
    
    async def send_to_admins(self, message: dict):
        """Send message to all admin connections"""
        for websocket in self.admin_connections:
            await self.send_personal_message(message, websocket)
    
    async def send_to_all(self, message: dict):
        """Send message to all connected clients"""
        for websocket in self.all_connections:
            await self.send_personal_message(message, websocket)
    
    async def broadcast_report_triaged(self, report_id: int, status: str, triaged_by: str, user_id: int):
        """Broadcast report triage update to relevant users"""
        # Notify the report submitter
        await self.send_to_user(user_id, {
            "type": "report_triaged",
            "data": {
                "report_id": report_id,
                "status": status,
                "triaged_by": triaged_by,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Notify all admins
        await self.send_to_admins({
            "type": "report_triaged",
            "data": {
                "report_id": report_id,
                "status": status,
                "triaged_by": triaged_by,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    async def broadcast_new_critical_report(self, report_data: dict):
        """Broadcast new critical report to all admins"""
        await self.send_to_admins({
            "type": "new_critical_report",
            "data": {
                "report_id": report_data["id"],
                "title": report_data["title"],
                "severity": report_data["severity"],
                "category": report_data["category"],
                "location": {
                    "lat": report_data["location_lat"],
                    "lng": report_data["location_lng"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    async def broadcast_emergency_alert(self, alert_data: dict):
        """Broadcast emergency alert to all users"""
        await self.send_to_all({
            "type": "emergency_alert",
            "data": {
                "title": alert_data["title"],
                "message": alert_data["message"],
                "severity": alert_data.get("severity", "HIGH"),
                "location": alert_data.get("location"),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    async def broadcast_system_notification(self, notification_data: dict):
        """Broadcast system notification to all users"""
        await self.send_to_all({
            "type": "system_notification",
            "data": {
                "title": notification_data["title"],
                "message": notification_data["message"],
                "level": notification_data.get("level", "info"),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.all_connections),
            "admin_connections": len(self.admin_connections),
            "user_connections": sum(len(connections) for connections in self.user_connections.values()),
            "unique_users": len(self.user_connections),
            "connected_users": [
                {
                    "user_id": metadata["user_id"],
                    "username": metadata["username"],
                    "role": metadata["role"],
                    "connected_at": metadata["connected_at"].isoformat()
                }
                for metadata in self.connection_metadata.values()
            ]
        }

# Global connection manager instance
connection_manager = AuthenticatedConnectionManager()
