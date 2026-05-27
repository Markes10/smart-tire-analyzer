"""
POST /feedback — User correction submission for self-correcting learning.
GET  /feedback/stats — Feedback statistics
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.request_models import FeedbackRequest
from app.models.response_models import FeedbackResponse
from app.database.crud import save_feedback, get_feedback_stats as get_db_feedback_stats, get_analysis_by_session
from app.services.continuous_learning_service import save_feedback_correction

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=FeedbackResponse,
    summary="Submit user correction",
    description=(
        "Submit a correction for a previous tire analysis. "
        "Corrections are stored and used for model retraining."
    ),
)
async def submit_feedback(request: FeedbackRequest):
    """
    Store user-corrected prediction for self-correcting learning pipeline.
    
    When enough corrections accumulate, triggers automatic model retraining.
    """
    logger.info(f"Feedback received for session: {request.session_id}")

    # Validate session exists
    if not request.session_id:
        raise HTTPException(status_code=422, detail="session_id is required")

    # Build feedback record
    corrected_prediction = {
        "tread_depth_mm": request.corrected_tread_depth_mm,
        "tread_depths_mm": request.corrected_tread_depths_mm,
        "wear_pattern": request.corrected_wear_pattern,
        "health_score": request.corrected_health_score,
    }
    feedback_record = {
        "session_id": request.session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user_corrected_tread_mm": request.corrected_tread_depth_mm,
        "user_corrected_tread_depths_mm": request.corrected_tread_depths_mm,
        "user_corrected_wear_pattern": request.corrected_wear_pattern,
        "user_corrected_health_score": request.corrected_health_score,
        "corrected_prediction": corrected_prediction,
        "original_prediction": request.original_prediction,
        "feedback_type": request.feedback_type,
        "confidence_override": request.confidence_override,
        "comment": request.comment,
    }

    analysis_report = await get_analysis_by_session(request.session_id)
    continuous_paths = {}
    try:
        continuous_paths = save_feedback_correction(
            session_id=request.session_id,
            analysis_report=analysis_report,
            feedback_record=feedback_record,
        )
        feedback_record.update(continuous_paths)
    except Exception as exc:
        logger.warning("Continuous-learning correction save failed for %s: %s", request.session_id, exc)

    # Save to feedback store
    feedback_id = await save_feedback(feedback_record)

    # Store as wrong prediction if marked as incorrect
    if request.feedback_type in ("wrong", "inaccurate"):
        from continuous_learning.wrong_predictions.store_wrong import store_wrong_prediction
        await store_wrong_prediction(request.session_id, feedback_record)

    # Queue retraining once enough corrected image rows exist.
    from continuous_learning.retraining.retrain_trigger import check_and_trigger_retrain, get_retrain_status
    retrain_triggered = await check_and_trigger_retrain()
    retrain_status = get_retrain_status()

    return JSONResponse(content={
        "feedback_id": feedback_id,
        "session_id": request.session_id,
        "stored": True,
        "retrain_triggered": retrain_triggered,
        "dataset_refresh_scheduled": retrain_status.get("refresh_running", False),
        "pending_learning_rows": retrain_status.get("pending_learning_rows", 0),
        "retrain_threshold": retrain_status.get("retrain_threshold", 10),
        "message": "Thank you for your feedback. It helps improve the model.",
    })


@router.get(
    "/stats",
    summary="Get feedback statistics",
)
async def get_stats():
    """Return feedback statistics for monitoring model drift."""
    stats = await get_db_feedback_stats()
    from continuous_learning.retraining.retrain_trigger import get_retrain_status

    retrain_status = get_retrain_status()
    pending_rows = int(retrain_status.get("pending_learning_rows", 0) or 0)
    threshold = int(retrain_status.get("retrain_threshold", 10) or 10)
    stats.update(
        {
            "pending_training": pending_rows,
            "pending_learning_rows": pending_rows,
            "trainable_learning_rows": retrain_status.get("trainable_learning_rows", 0),
            "retrain_threshold": threshold,
            "retrain_ready": pending_rows >= threshold,
            "dataset_refresh_scheduled": retrain_status.get("refresh_running", False),
            "retrain_running": retrain_status.get("retrain_running", False),
            "auto_retrain": retrain_status.get("auto_retrain", True),
            "auto_retrain_refresh": retrain_status.get("auto_retrain_refresh", False),
            "corrections_needed": max(0, threshold - pending_rows),
        }
    )
    return JSONResponse(content=stats)


@router.get(
    "/retrain/status",
    summary="Get automatic retraining status",
)
async def get_retraining_status():
    """Return continuous-learning dataset refresh and retraining status."""
    from continuous_learning.retraining.retrain_trigger import get_retrain_status

    return JSONResponse(content=get_retrain_status())
