"""
Database CRUD Operations — Read/Write for analysis results and feedback.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import select, desc, and_
from app.database.db import AsyncSessionLocal, ensure_database_ready
from app.database.models import AnalysisResult, FeedbackRecord

logger = logging.getLogger(__name__)


async def save_analysis_result(report: Dict) -> str:
    """Save a complete analysis report to the database."""
    await ensure_database_ready()
    async with AsyncSessionLocal() as db:
        try:
            predictions = report.get("predictions", {})
            tread = predictions.get("tread_depths_mm", {})
            wear = predictions.get("wear_pattern", {})
            meta = report.get("metadata", {})

            record = AnalysisResult(
                id=str(uuid.uuid4()),
                session_id=report["session_id"],
                timestamp=datetime.utcnow(),
                health_score=predictions.get("health_score"),
                avg_tread_mm=tread.get("average"),
                remaining_life_km=predictions.get("remaining_life_km"),
                wear_pattern_label=wear.get("label"),
                wear_pattern_severity=wear.get("severity"),
                risk_level=report.get("risk_level"),
                replace_immediately=report.get("replace_immediately", False),
                confidence=report.get("confidence"),
                full_report=report,
                latitude=meta.get("latitude"),
                longitude=meta.get("longitude"),
                weather_condition=report.get("context", {}).get("weather_condition"),
                tire_brand=meta.get("tire_brand"),
                tire_model=meta.get("tire_model"),
                tire_size=meta.get("tire_size"),
                image_filename=meta.get("image_filename"),
                model_version=report.get("model_version"),
            )
            db.add(record)
            await db.commit()
            return record.session_id
        except Exception as e:
            logger.error(f"DB save error: {e}")
            await db.rollback()
            return ""


async def get_analysis_by_session(session_id: str) -> Optional[Dict]:
    """Retrieve a single analysis result by session ID."""
    await ensure_database_ready()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AnalysisResult).where(AnalysisResult.session_id == session_id)
        )
        record = result.scalar_one_or_none()
        if record:
            return record.full_report
        return None


async def get_analysis_history(
    page: int = 1,
    page_size: int = 20,
    risk_level: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict:
    """Retrieve paginated analysis history with optional filters."""
    await ensure_database_ready()
    async with AsyncSessionLocal() as db:
        query = select(AnalysisResult).order_by(desc(AnalysisResult.timestamp))

        filters = []
        if risk_level:
            filters.append(AnalysisResult.risk_level == risk_level.upper())
        if from_date:
            filters.append(AnalysisResult.timestamp >= datetime.fromisoformat(from_date))
        if to_date:
            filters.append(AnalysisResult.timestamp <= datetime.fromisoformat(to_date))
        if filters:
            query = query.where(and_(*filters))

        # Count total
        count_result = await db.execute(select(AnalysisResult.id).where(and_(*filters) if filters else True))
        total = len(count_result.all())

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        results = await db.execute(query)
        records = results.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "session_id": r.session_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "risk_level": r.risk_level,
                    "health_score": r.health_score,
                    "avg_tread_mm": r.avg_tread_mm,
                    "remaining_life_km": r.remaining_life_km,
                    "wear_pattern": r.wear_pattern_label,
                }
                for r in records
            ],
        }


async def save_feedback(feedback: Dict) -> str:
    """Save user feedback/correction to the database."""
    await ensure_database_ready()
    async with AsyncSessionLocal() as db:
        try:
            record = FeedbackRecord(
                id=str(uuid.uuid4()),
                session_id=feedback["session_id"],
                feedback_type=feedback["feedback_type"],
                corrected_tread_mm=feedback.get("user_corrected_tread_mm"),
                corrected_wear_pattern=feedback.get("user_corrected_wear_pattern"),
                corrected_health_score=feedback.get("user_corrected_health_score"),
                confidence_override=feedback.get("confidence_override"),
                comment=feedback.get("comment"),
                original_prediction=feedback.get("original_prediction"),
                corrected_prediction=feedback.get("corrected_prediction"),
            )
            db.add(record)
            await db.commit()
            return record.id
        except Exception as e:
            logger.error(f"Feedback save error: {e}")
            await db.rollback()
            return str(uuid.uuid4())


async def get_feedback_stats() -> Dict:
    """Return feedback statistics for monitoring."""
    await ensure_database_ready()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FeedbackRecord))
        records = result.scalars().all()
        total = len(records)
        wrong = sum(1 for r in records if r.feedback_type in ("wrong", "inaccurate"))
        correct = sum(1 for r in records if r.feedback_type == "correct")
        return {
            "total_feedback": total,
            "wrong_predictions": wrong,
            "correct_predictions": correct,
            "accuracy_rate": round(correct / max(total, 1), 4),
            "retrain_threshold": 50,
            "retrain_ready": wrong >= 50,
        }
