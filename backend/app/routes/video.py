"""
Video analysis routes for drive-through tire inspection.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.services.video_analysis_service import VideoAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/video", tags=["Video Analysis"])

_video_service: VideoAnalysisService | None = None


def get_video_service(inference_service=None):
    global _video_service
    if _video_service is None and inference_service:
        _video_service = VideoAnalysisService(inference_service)
    return _video_service


@router.post("/analyze-frame")
async def analyze_frame(
    image: UploadFile = File(...),
    frame_id: int = 0,
):
    """Analyze a single video frame."""
    svc = get_video_service()
    if svc is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Video analysis service not initialized"},
        )
    
    frame_bytes = await image.read()
    result = await svc.process_frame(frame_bytes, frame_id)
    return JSONResponse(content=result)


@router.websocket("/stream")
async def video_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time video frame streaming."""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info("Video stream connected: %s", session_id)
    
    svc = get_video_service()
    if svc is None:
        await websocket.send_json({"error": "Service not initialized"})
        await websocket.close()
        return
    
    svc.reset()
    frame_count = 0
    
    try:
        while True:
            data = await websocket.receive_bytes()
            result = await svc.process_frame(data, frame_count)
            await websocket.send_json(result)
            frame_count += 1
    except WebSocketDisconnect:
        logger.info("Video stream disconnected: %s (%d frames)", session_id, frame_count)
    except Exception as exc:
        logger.warning("Video stream error: %s", exc)
