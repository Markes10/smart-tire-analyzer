"""
Feedback Service — Handles feedback storage, stats, and retrain coordination.
Central module used by both the API route and the retrain trigger.
"""

import json
import uuid
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

WRONG_LOG_PATH = Path("continuous_learning/wrong_predictions/wrong_log.json")
RETRAIN_THRESHOLD = 50  # Trigger retrain after N wrong predictions


def _load_feedback_log() -> list:
    """Load the wrong prediction log from disk."""
    if not WRONG_LOG_PATH.exists():
        return []
    try:
        with open(WRONG_LOG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_feedback_log(entries: list):
    """Save the wrong prediction log to disk."""
    WRONG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WRONG_LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def store_feedback(
    session_id: str,
    feedback_type: str,
    corrected_tread_depth_mm: Optional[float],
    corrected_wear_pattern: Optional[str],
    corrected_health_score: Optional[float],
    original_prediction: Optional[Dict] = None,
    comment: Optional[str] = None,
) -> Dict:
    """
    Store a user feedback record and check retrain threshold.

    Returns:
        Dict with feedback_id, stored status, and retrain info
    """
    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
    entry = {
        "feedback_id": feedback_id,
        "session_id": session_id,
        "feedback_type": feedback_type,
        "timestamp": datetime.utcnow().isoformat(),
        "corrected_tread_depth_mm": corrected_tread_depth_mm,
        "corrected_wear_pattern": corrected_wear_pattern,
        "corrected_health_score": corrected_health_score,
        "original_prediction": original_prediction or {},
        "comment": comment,
        "used_for_training": False,
    }

    # Load, append, save
    log = _load_feedback_log()
    log.append(entry)
    _save_feedback_log(log)

    # Count wrong predictions (exclude "correct" feedback)
    wrong_count = sum(
        1 for e in log
        if e.get("feedback_type") in ("wrong", "inaccurate")
        and not e.get("used_for_training", False)
    )
    retrain_ready = wrong_count >= RETRAIN_THRESHOLD

    logger.info(
        f"Feedback stored: {feedback_id} | type={feedback_type} | "
        f"wrong_count={wrong_count}/{RETRAIN_THRESHOLD}"
    )

    if retrain_ready:
        logger.info(f"Retrain threshold reached ({wrong_count} corrections) — triggering")
        _trigger_background_retrain()

    return {
        "feedback_id": feedback_id,
        "session_id": session_id,
        "stored": True,
        "wrong_count": wrong_count,
        "retrain_triggered": retrain_ready,
        "message": (
            f"Retrain triggered — {wrong_count} corrections collected."
            if retrain_ready else
            f"Feedback stored. {wrong_count} of {RETRAIN_THRESHOLD} corrections before next retrain."
        ),
    }


def get_feedback_stats() -> Dict:
    """Compute feedback statistics from the log file."""
    log = _load_feedback_log()
    total = len(log)
    wrong = sum(1 for e in log if e.get("feedback_type") in ("wrong", "inaccurate"))
    correct = sum(1 for e in log if e.get("feedback_type") == "correct")
    untrained = sum(1 for e in log if not e.get("used_for_training", False))

    accuracy_rate = round(correct / max(total, 1) * 100, 1)
    retrain_ready = untrained >= RETRAIN_THRESHOLD

    # Pattern distribution of corrections
    pattern_counts: Dict[str, int] = {}
    for entry in log:
        wp = entry.get("corrected_wear_pattern")
        if wp:
            pattern_counts[wp] = pattern_counts.get(wp, 0) + 1

    return {
        "total_feedback": total,
        "wrong_predictions": wrong,
        "correct_predictions": correct,
        "accuracy_rate": accuracy_rate,
        "pending_training": untrained,
        "retrain_ready": retrain_ready,
        "corrections_needed": max(0, RETRAIN_THRESHOLD - untrained),
        "correction_pattern_distribution": pattern_counts,
    }


def mark_feedback_used(feedback_ids: list):
    """Mark feedback entries as used for training (prevents re-training on same data)."""
    log = _load_feedback_log()
    updated = 0
    for entry in log:
        if entry["feedback_id"] in feedback_ids:
            entry["used_for_training"] = True
            updated += 1
    _save_feedback_log(log)
    logger.info(f"Marked {updated} feedback entries as used for training")


def get_pending_corrections() -> list:
    """Get all unused wrong predictions for the training pipeline."""
    log = _load_feedback_log()
    return [
        e for e in log
        if e.get("feedback_type") in ("wrong", "inaccurate")
        and not e.get("used_for_training", False)
    ]


def _trigger_background_retrain():
    """Trigger incremental retraining in the background (non-blocking)."""
    try:
        import threading
        from continuous_learning.retraining.incremental_train import run_incremental_training

        thread = threading.Thread(
            target=run_incremental_training,
            kwargs={"data_dir": "continuous_learning/wrong_predictions"},
            daemon=True,
            name="RetrainThread",
        )
        thread.start()
        logger.info("Background retrain thread started")
    except Exception as e:
        logger.error(f"Failed to start retrain thread: {e}")
