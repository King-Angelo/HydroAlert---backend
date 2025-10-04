from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from app.websocket.auth import websocket_auth
from app.websocket.connection_manager import connection_manager
from app.core.dependencies import get_user_by_username
from app.database import get_session
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/realtime")
async def websocket_realtime(websocket: WebSocket, token: str = Query(...)):
    """Authenticated WebSocket endpoint for real-time updates"""
    try:
        # Authenticate the WebSocket connection
        user = await websocket_auth.authenticate_websocket(websocket, token)
        if not user:
            await websocket_auth.close_unauthorized_connection(
                websocket, "Invalid or missing authentication token"
            )
            return
        
        # Connect the authenticated user
        await connection_manager.connect(websocket, user)
        
        try:
            while True:
                # Listen for incoming messages
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    
                    # Handle ping/pong for connection health
                    if message.get("type") == "ping":
                        await connection_manager.send_personal_message({
                            "type": "pong",
                            "data": {"timestamp": "now"}
                        }, websocket)
                    
                    # Handle other message types as needed
                    elif message.get("type") == "echo":
                        await connection_manager.send_personal_message({
                            "type": "echo_response",
                            "data": {"message": message.get("data", {}).get("message", "")}
                        }, websocket)
                    
                    else:
                        # Unknown message type
                        await connection_manager.send_personal_message({
                            "type": "error",
                            "data": {"message": "Unknown message type"}
                        }, websocket)
                        
                except json.JSONDecodeError:
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "data": {"message": "Invalid JSON format"}
                    }, websocket)
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user: {user.username}")
        finally:
            connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
        except:
            pass


@router.websocket("/admin")
async def websocket_admin(websocket: WebSocket, token: str = Query(...)):
    """Admin-only WebSocket endpoint for administrative functions"""
    try:
        # Authenticate the WebSocket connection
        user = await websocket_auth.authenticate_websocket(websocket, token)
        if not user:
            await websocket_auth.close_unauthorized_connection(
                websocket, "Authentication required"
            )
            return
        
        # Check admin privileges
        if not await websocket_auth.authorize_admin_broadcast(user):
            await websocket_auth.close_unauthorized_connection(
                websocket, "Admin privileges required"
            )
            return
        
        # Connect the admin user
        await connection_manager.connect(websocket, user)
        
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    
                    # Handle admin-specific messages
                    if message.get("type") == "ping":
                        await connection_manager.send_personal_message({
                            "type": "pong",
                            "data": {"timestamp": "now", "role": "admin"}
                        }, websocket)
                    
                    elif message.get("type") == "get_stats":
                        stats = connection_manager.get_connection_stats()
                        await connection_manager.send_personal_message({
                            "type": "connection_stats",
                            "data": stats
                        }, websocket)
                    
                    else:
                        await connection_manager.send_personal_message({
                            "type": "error",
                            "data": {"message": "Unknown admin message type"}
                        }, websocket)
                        
                except json.JSONDecodeError:
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "data": {"message": "Invalid JSON format"}
                    }, websocket)
                    
        except WebSocketDisconnect:
            logger.info(f"Admin WebSocket disconnected for user: {user.username}")
        finally:
            connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"Admin WebSocket error: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
        except:
            pass


# Legacy endpoints for backward compatibility
@router.websocket("/flood-updates")
async def websocket_flood_updates_legacy(websocket: WebSocket):
    """Legacy WebSocket endpoint - redirects to authenticated endpoint"""
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION, 
        reason="This endpoint requires authentication. Use /ws/realtime?token=<jwt>"
    )


@router.websocket("/flood-updates/{user_id}")
async def websocket_user_updates_legacy(websocket: WebSocket, user_id: str):
    """Legacy WebSocket endpoint - redirects to authenticated endpoint"""
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION, 
        reason="This endpoint requires authentication. Use /ws/realtime?token=<jwt>"
    )