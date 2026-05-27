"""
Wrong Prediction Storage — Self-Correcting Learning Pipeline.
Logs low-confidence and user-corrected predictions for retraining.
"""

import json
import uuid
import logging
import asyncio
from json import JSONDecodeError
from datetime import datetime
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

WRONG_LOG_PATH = Path("continuous_learning/wrong_predictions/wrong_log.json")
WRONG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _empty_log() -> Dict:
    return {"records": [], "total": 0, "last_updated": None}


def _load_log() -> Dict:
    """Load the wrong-prediction log, recovering from empty/corrupt files."""
    if not WRONG_LOG_PATH.exists() or WRONG_LOG_PATH.stat().st_size == 0:
        return _empty_log()

    try:
        with WRONG_LOG_PATH.open("r", encoding="utf-8-sig") as f:
            log = json.load(f)
    except (JSONDecodeError, OSError) as exc:
        logger.warning("Wrong prediction log could not be read; starting a fresh log: %s", exc)
        return _empty_log()

    if not isinstance(log, dict):
        return _empty_log()
    if not isinstance(log.get("records"), list):
        log["records"] = []
    log["total"] = int(log.get("total") or len(log["records"]))
    log.setdefault("last_updated", None)
    return log

CONFIDENCE_THRESHOLD = 0.65  # Below this → log as wrong prediction


async def store_wrong_prediction(session_id: str, data: Dict) -> str:
    """
    Store a wrong/low-confidence prediction in the wrong prediction log.
    
    Args:
        session_id: Analysis session ID
        data: Dict containing prediction + feedback info
    
    Returns:
        ID of the stored wrong prediction record
    """
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "source": data.get("feedback_type", "low_confidence"),
        "original_prediction": data.get("original_prediction"),
        "corrected_prediction": data.get("corrected_prediction"),
        "image_path": data.get("continuous_learning_image_path"),
        "labels_path": data.get("continuous_learning_labels_path"),
        "correction_path": data.get("continuous_learning_correction_path"),
        "user_correction": {
            "tread_depth_mm": data.get("user_corrected_tread_mm"),
            "tread_depths_mm": data.get("user_corrected_tread_depths_mm"),
            "wear_pattern": data.get("user_corrected_wear_pattern"),
            "health_score": data.get("user_corrected_health_score"),
        },
        "confidence_override": data.get("confidence_override"),
        "comment": data.get("comment"),
    }

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _append_to_log, record)
    logger.info(f"Wrong prediction stored: {record_id} (session={session_id})")
    return record_id


def _append_to_log(record: Dict):
    """Thread-safe append to the wrong prediction JSONL log."""
    try:
        log = _load_log()

        log["records"].append(record)
        log["total"] = len(log["records"])
        log["last_updated"] = datetime.utcnow().isoformat()

        temp_path = WRONG_LOG_PATH.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)
        temp_path.replace(WRONG_LOG_PATH)
    except Exception as e:
        logger.error(f"Failed to write wrong log: {e}")


def get_wrong_count() -> int:
    """Return current count of logged wrong predictions."""
    log = _load_log()
    return log.get("total", 0)


def load_wrong_predictions(min_confidence: float = CONFIDENCE_THRESHOLD) -> list:
    """Load all stored wrong predictions for retraining."""
    log = _load_log()
    return log.get("records", [])


def should_log_as_wrong(confidence: float) -> bool:
    """Check if a prediction confidence is low enough to log."""
    return confidence < CONFIDENCE_THRESHOLD
