"""
Response Models — Pydantic schemas for API responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class TreadDepths(BaseModel):
    tread_1: float
    tread_2: float
    tread_3: float
    tread_4: float
    average: float
    min: float
    max: float


class WearPattern(BaseModel):
    class_id: int
    label: str
    cause: str
    severity: str
    confidence: float
    probabilities: Optional[Dict[str, float]] = None


class Predictions(BaseModel):
    tread_depths_mm: TreadDepths
    health_score: float
    remaining_life_km: float
    remaining_life_km_raw: Optional[float] = None
    wear_pattern: WearPattern


class Context(BaseModel):
    terrain_type: Optional[str] = None
    road_condition: Optional[str] = None
    road_condition_basis: Optional[str] = None
    traffic_density: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    visibility_km: Optional[float] = None
    rain_detected: Optional[bool] = None
    road_wear_multiplier: Optional[float] = None
    weather_risk_multiplier: Optional[float] = None
    route_source_latitude: Optional[float] = None
    route_source_longitude: Optional[float] = None
    route_destination_latitude: Optional[float] = None
    route_destination_longitude: Optional[float] = None
    route_distance_km: Optional[float] = None
    route_duration_min: Optional[float] = None
    route_analysis_source: Optional[str] = None
    street_view_available: Optional[bool] = None
    street_view_sample_count: Optional[int] = None
    street_view_covered_samples: Optional[int] = None
    street_view_visual_summary: Optional[str] = None
    street_view_samples: Optional[List[Dict[str, Any]]] = None


class Reasoning(BaseModel):
    source: str
    risk_level: str
    driving_advice: str
    replacement_recommended: bool
    replacement_urgency: Optional[str] = None
    primary_cause: Optional[str] = None
    additional_notes: Optional[str] = None
    safety_score: Optional[int] = None


class Alert(BaseModel):
    level: str
    message: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    timestamp: str
    model_version: Optional[str] = None
    risk_level: str
    status: str
    replace_immediately: bool
    confidence: float
    predictions: Predictions
    context: Optional[Context] = None
    reasoning: Reasoning
    alerts: List[Alert]
    metadata: Optional[Dict[str, Any]] = None
    enterprise_ai: Optional[Dict[str, Any]] = None
    blur_score: Optional[float] = None
    source: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    session_id: str
    stored: bool
    retrain_triggered: bool
    dataset_refresh_scheduled: Optional[bool] = None
    pending_learning_rows: Optional[int] = None
    retrain_threshold: Optional[int] = None
    message: str
