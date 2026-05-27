"""
Pydantic Request Models — Input validation for all API endpoints.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class FeedbackRequest(BaseModel):
    """Request body for POST /feedback"""
    session_id: str = Field(..., description="ID of the analysis session being corrected")
    feedback_type: str = Field(
        ...,
        description="Type of feedback: 'wrong', 'inaccurate', 'correct', 'partial'",
    )
    corrected_tread_depth_mm: Optional[float] = Field(
        None,
        ge=0.0,
        le=12.0,
        description="User-provided actual tread depth in mm",
    )
    corrected_tread_depths_mm: Optional[Dict[str, float]] = Field(
        None,
        description="Optional per-position tread depths: tread_1, tread_2, tread_3, tread_4",
    )
    corrected_wear_pattern: Optional[str] = Field(
        None,
        description="User-identified wear pattern class",
    )
    corrected_health_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="User-provided health score override",
    )
    original_prediction: Optional[Dict[str, Any]] = Field(
        None,
        description="Original prediction dict (for diff logging)",
    )
    confidence_override: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="User's confidence in their correction (0-1)",
    )
    comment: Optional[str] = Field(
        None,
        max_length=1000,
        description="Free-text comment from user",
    )

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v):
        allowed = {"wrong", "inaccurate", "correct", "partial"}
        if v.lower() not in allowed:
            raise ValueError(f"feedback_type must be one of: {allowed}")
        return v.lower()

    @field_validator("corrected_tread_depths_mm")
    @classmethod
    def validate_tread_depths(cls, value):
        if value is None:
            return value
        allowed = {"tread_1", "tread_2", "tread_3", "tread_4"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"corrected_tread_depths_mm supports only: {sorted(allowed)}")
        for key, depth in value.items():
            if depth < 0.0 or depth > 12.0:
                raise ValueError(f"{key} must be between 0 and 12 mm")
        return value


class AnalyzeRequest(BaseModel):
    """Metadata fields for POST /analyze (multipart form supplement)"""
    tire_brand: Optional[str] = Field(None, max_length=100)
    tire_model: Optional[str] = Field(None, max_length=100)
    tire_size: Optional[str] = Field(None, max_length=20, description="e.g. '185/65 R15'")
    mileage_km: Optional[float] = Field(None, ge=0)
    tire_pressure_psi: Optional[float] = Field(None, ge=0, le=120)
    temperature_c: Optional[float] = Field(None, ge=-40, le=150)
    vibration_g: Optional[float] = Field(None, ge=0, le=20)
    speed_kmph: Optional[float] = Field(None, ge=0, le=350)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    source_latitude: Optional[float] = Field(None, ge=-90, le=90)
    source_longitude: Optional[float] = Field(None, ge=-180, le=180)
    destination_latitude: Optional[float] = Field(None, ge=-90, le=90)
    destination_longitude: Optional[float] = Field(None, ge=-180, le=180)


class RetrainRequest(BaseModel):
    """Request body for manual retrain trigger."""
    force: bool = Field(False, description="Force retraining even if threshold not met")
    version_tag: Optional[str] = Field(None, description="Tag for new model version")
