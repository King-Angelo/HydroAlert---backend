from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from app.core.websocket import manager
from app.core.dependencies import get_current_user
from app.models.user import User
import json

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/flood-updates")
async def websocket_flood_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time flood updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": "2024-01-01T00:00:00Z"}),
                    websocket
                )
            elif message.get("type") == "subscribe":
                # Handle subscription to specific updates
                await manager.send_personal_message(
                    json.dumps({"type": "subscribed", "channel": message.get("channel")}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/flood-updates/{user_id}")
async def websocket_user_updates(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for user-specific flood updates"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "user_id": user_id}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.post("/broadcast-flood-update")
async def broadcast_flood_update(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Broadcast flood update to all connected clients (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    await manager.send_flood_update(data)
    return {"message": "Flood update broadcasted", "recipients": len(manager.active_connections)}


@router.post("/broadcast-alert")
async def broadcast_alert(
    alert_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Broadcast emergency alert to all connected clients (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    await manager.send_alert(alert_data)
    return {"message": "Alert broadcasted", "recipients": len(manager.active_connections)}
