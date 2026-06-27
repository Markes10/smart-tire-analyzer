"""
Real-time video frame analysis for drive-through tire inspection.
Processes video frames sequentially with temporal smoothing.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, AsyncIterator, Optional

import numpy as np

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    """
    Processes video frames for tire analysis with temporal smoothing.
    Designed for drive-through inspection scenarios.
    """
    
    def __init__(self, inference_service, window_size: int = 5):
        self._inference = inference_service
        self._window_size = window_size
        self._frame_buffer: deque = deque(maxlen=window_size)
        self._prediction_buffer: deque = deque(maxlen=window_size)
    
    async def process_frame(self, frame_bytes: bytes, frame_id: int) -> dict[str, Any]:
        """Process a single video frame and return prediction."""
        try:
            import cv2
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"frame_id": frame_id, "error": "Invalid frame data"}
            
            result = await self._inference.predict(
                image_bytes=cv2.imencode('.jpg', frame)[1].tobytes(),
                session_id=f"video-{frame_id}",
                context_data={"source": "video_stream"},
            )
            
            self._frame_buffer.append(frame_id)
            self._prediction_buffer.append(result)
            
            return {
                "frame_id": frame_id,
                "predictions": result,
                "smoothed": self._get_smoothed(),
            }
        except Exception as exc:
            logger.warning("Frame %d processing failed: %s", frame_id, exc)
            return {"frame_id": frame_id, "error": str(exc)}
    
    def _get_smoothed(self) -> Optional[dict]:
        """Return temporally smoothed predictions from buffer."""
        if len(self._prediction_buffer) < 2:
            return None
        
        depths = []
        healths = []
        
        for pred in self._prediction_buffer:
            if isinstance(pred, dict):
                td = pred.get("predictions", {}).get("tread_depths_mm", {})
                if isinstance(td, dict) and "average" in td:
                    depths.append(td["average"])
                hs = pred.get("predictions", {}).get("health_score")
                if hs is not None:
                    healths.append(hs)
        
        if not depths:
            return None
        
        return {
            "smoothed_avg_tread_mm": float(np.mean(depths)),
            "smoothed_health_score": float(np.mean(healths)) if healths else None,
            "frames_analyzed": len(self._prediction_buffer),
            "confidence": "high" if len(self._prediction_buffer) >= 3 else "low",
        }
    
    async def streaming_analyze(
        self, frame_iterator: AsyncIterator[tuple[bytes, int]]
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a stream of frames and yield results."""
        async for frame_bytes, frame_id in frame_iterator:
            result = await self.process_frame(frame_bytes, frame_id)
            yield result
    
    def reset(self):
        """Clear buffers for a new vehicle."""
        self._frame_buffer.clear()
        self._prediction_buffer.clear()
        logger.info("Video analysis buffers reset")
