from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from app.websocket.auth import websocket_auth
from app.websocket.connection_manager import connection_manager
from app.websocket.map_events import map_event_broadcaster
from app.schemas.map import MapBounds
from app.core.dependencies import get_user_by_username
from app.database import get_session
import json
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["map-websocket"])

@router.websocket("/map")
async def websocket_map(
    websocket: WebSocket, 
    token: str = Query(...),
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180)
):
    """Map-specific WebSocket endpoint with viewport registration"""
    connection_id = str(uuid.uuid4())
    
    try:
        # Authenticate the WebSocket connection
        user = await websocket_auth.authenticate_websocket(websocket, token)
        if not user:
            await websocket_auth.close_unauthorized_connection(
                websocket, "Invalid or missing authentication token"
            )
            return
        
        # Validate bounds
        if north <= south or east <= west:
            await websocket_auth.close_unauthorized_connection(
                websocket, "Invalid map bounds provided"
            )
            return
        
        # Create map bounds from query parameters
        map_bounds = MapBounds(north=north, south=south, east=east, west=west)
        
        # Connect the authenticated user
        await connection_manager.connect(websocket, user)
        
        # Register viewport for map events
        map_event_broadcaster.register_viewport(connection_id, map_bounds)
        
        # Send welcome message with connection info
        await connection_manager.send_personal_message({
            "type": "map_connection_established",
            "data": {
                "message": "Map WebSocket connection established",
                "user": user.username,
                "role": user.role,
                "connection_id": connection_id,
                "viewport": {
                    "north": map_bounds.north,
                    "south": map_bounds.south,
                    "east": map_bounds.east,
                    "west": map_bounds.west
                },
                "timestamp": "now"
            }
        }, websocket)
        
        try:
            while True:
                # Listen for incoming messages
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    
                    # Handle viewport updates
                    if message.get("type") == "viewport_update":
                        new_bounds = MapBounds(**message.get("data", {}).get("viewport", {}))
                        map_event_broadcaster.register_viewport(connection_id, new_bounds)
                        
                        await connection_manager.send_personal_message({
                            "type": "viewport_updated",
                            "data": {
                                "connection_id": connection_id,
                                "viewport": {
                                    "north": new_bounds.north,
                                    "south": new_bounds.south,
                                    "east": new_bounds.east,
                                    "west": new_bounds.west
                                },
                                "timestamp": "now"
                            }
                        }, websocket)
                    
                    # Handle ping/pong for connection health
                    elif message.get("type") == "ping":
                        await connection_manager.send_personal_message({
                            "type": "pong",
                            "data": {
                                "connection_id": connection_id,
                                "timestamp": "now"
                            }
                        }, websocket)
                    
                    # Handle map data refresh request
                    elif message.get("type") == "request_refresh":
                        await connection_manager.send_personal_message({
                            "type": "refresh_requested",
                            "data": {
                                "message": "Map data refresh requested",
                                "connection_id": connection_id,
                                "timestamp": "now"
                            }
                        }, websocket)
                    
                    # Handle get viewport stats (admin only)
                    elif message.get("type") == "get_viewport_stats" and user.role == "admin":
                        stats = map_event_broadcaster.get_viewport_stats()
                        await connection_manager.send_personal_message({
                            "type": "viewport_stats",
                            "data": {
                                "stats": stats,
                                "connection_id": connection_id,
                                "timestamp": "now"
                            }
                        }, websocket)
                    
                    else:
                        # Unknown message type
                        await connection_manager.send_personal_message({
                            "type": "error",
                            "data": {
                                "message": "Unknown message type",
                                "connection_id": connection_id
                            }
                        }, websocket)
                        
                except json.JSONDecodeError:
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "message": "Invalid JSON format",
                            "connection_id": connection_id
                        }
                    }, websocket)
                    
        except WebSocketDisconnect:
            logger.info(f"Map WebSocket disconnected for user: {user.username}")
        finally:
            # Unregister viewport and disconnect
            map_event_broadcaster.unregister_viewport(connection_id)
            connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"Map WebSocket error: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
        except:
            pass
