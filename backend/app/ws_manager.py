"""
WebSocket connection manager for real-time analysis updates.
"""

import json
import logging
from typing import Any, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self._connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)
        logger.debug("WebSocket connected: %s", id(websocket))
    
    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)
        logger.debug("WebSocket disconnected: %s", id(websocket))
    
    async def broadcast(self, message: dict[str, Any]):
        stale = set()
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self._connections.discard(ws)
    
    async def send_to(self, websocket: WebSocket, message: dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.warning("WebSocket send failed: %s", exc)
            self.disconnect(websocket)

manager = ConnectionManager()
