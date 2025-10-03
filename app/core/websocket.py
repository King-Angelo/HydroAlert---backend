from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

    async def send_to_user(self, message: str, user_id: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    self.user_connections[user_id].remove(connection)

    async def send_flood_update(self, data: Dict[str, Any]):
        """Send flood update to all connected clients"""
        message = json.dumps({
            "type": "flood_update",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
        await self.broadcast(message)

    async def send_alert(self, alert_data: Dict[str, Any]):
        """Send emergency alert to all connected clients"""
        message = json.dumps({
            "type": "emergency_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        await self.broadcast(message)


manager = ConnectionManager()
