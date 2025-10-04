from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from typing import Optional, Dict, List
from app.core.security import verify_token
from app.models.user import User
from app.core.dependencies import get_user_by_username
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
import logging

logger = logging.getLogger(__name__)

class WebSocketAuth:
    """WebSocket authentication and authorization handler"""
    
    def __init__(self):
        self.authenticated_connections: Dict[WebSocket, User] = {}
        self.connection_tokens: Dict[WebSocket, str] = {}
    
    async def authenticate_websocket(self, websocket: WebSocket, token: str) -> Optional[User]:
        """
        Authenticate WebSocket connection using JWT token
        Returns User object if authentication successful, None otherwise
        """
        try:
            # Verify JWT token
            token_data = verify_token(token)
            if not token_data:
                logger.warning("Invalid JWT token provided for WebSocket connection")
                return None
            
            # Get user from database
            async for session in get_session():
                user = await get_user_by_username(token_data.username, session)
                if not user or not user.is_active:
                    logger.warning(f"User {token_data.username} not found or inactive")
                    return None
                
                # Store authenticated connection
                self.authenticated_connections[websocket] = user
                self.connection_tokens[websocket] = token
                
                logger.info(f"WebSocket authenticated for user: {user.username} (role: {user.role})")
                return user
                
        except Exception as e:
            logger.error(f"WebSocket authentication error: {str(e)}")
            return None
    
    async def authorize_admin_broadcast(self, user: User) -> bool:
        """Check if user has admin privileges for broadcasting"""
        return user.role == "admin"
    
    async def get_user_channels(self, user: User) -> List[str]:
        """Get list of channels user is authorized to access"""
        channels = ["global", f"user_{user.id}"]
        
        if user.role == "admin":
            channels.extend(["admin", "broadcast"])
        
        return channels
    
    def get_authenticated_user(self, websocket: WebSocket) -> Optional[User]:
        """Get authenticated user for a WebSocket connection"""
        return self.authenticated_connections.get(websocket)
    
    def is_admin_connection(self, websocket: WebSocket) -> bool:
        """Check if WebSocket connection belongs to an admin user"""
        user = self.get_authenticated_user(websocket)
        return user and user.role == "admin"
    
    def remove_connection(self, websocket: WebSocket):
        """Remove WebSocket connection from authenticated connections"""
        if websocket in self.authenticated_connections:
            user = self.authenticated_connections[websocket]
            logger.info(f"Removing WebSocket connection for user: {user.username}")
            del self.authenticated_connections[websocket]
        
        if websocket in self.connection_tokens:
            del self.connection_tokens[websocket]
    
    async def close_unauthorized_connection(self, websocket: WebSocket, reason: str = "Authentication failed"):
        """Close WebSocket connection due to authorization failure"""
        try:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
            logger.warning(f"Closed unauthorized WebSocket connection: {reason}")
        except Exception as e:
            logger.error(f"Error closing WebSocket connection: {str(e)}")

# Global WebSocket authentication instance
websocket_auth = WebSocketAuth()
