"""
Database Models — SQLAlchemy table definitions.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON
from app.database.db import Base


def gen_uuid():
    return str(uuid.uuid4())


class AnalysisResult(Base):
    """Stores each tire analysis session result."""
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Core predictions
    health_score = Column(Float, nullable=True)
    avg_tread_mm = Column(Float, nullable=True)
    remaining_life_km = Column(Float, nullable=True)
    wear_pattern_label = Column(String(64), nullable=True)
    wear_pattern_severity = Column(String(32), nullable=True)
    risk_level = Column(String(16), nullable=True)
    replace_immediately = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)

    # Full report JSON
    full_report = Column(JSON, nullable=True)

    # Context
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    weather_condition = Column(String(64), nullable=True)

    # Metadata
    tire_brand = Column(String(128), nullable=True)
    tire_model = Column(String(128), nullable=True)
    tire_size = Column(String(32), nullable=True)
    image_filename = Column(String(256), nullable=True)
    model_version = Column(String(32), nullable=True)


class FeedbackRecord(Base):
    """Stores user corrections for the continuous learning pipeline."""
    __tablename__ = "feedback_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    feedback_type = Column(String(32), nullable=False)

    # User corrections
    corrected_tread_mm = Column(Float, nullable=True)
    corrected_wear_pattern = Column(String(64), nullable=True)
    corrected_health_score = Column(Float, nullable=True)
    confidence_override = Column(Float, nullable=True)
    comment = Column(Text, nullable=True)

    # Original prediction for diff
    original_prediction = Column(JSON, nullable=True)
    corrected_prediction = Column(JSON, nullable=True)
