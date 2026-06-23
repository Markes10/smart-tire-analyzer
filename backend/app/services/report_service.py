"""
Report Service — Builds the final Smart Tire Report JSON.
Combines model predictions, context, Gemini reasoning, and alerts.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from ai_model.ann.output_heads import compute_risk_level, _generate_alerts, _rule_based_reasoning

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"


class ReportService:
    """Constructs the canonical Smart Tire Analysis Report."""

    def build_report(
        self,
        session_id: str,
        prediction_result: Dict,
        context: Dict,
        gemini_reasoning: Optional[Dict],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Assemble complete analysis report from all data sources.

        Args:
            session_id: Unique analysis session UUID
            prediction_result: Raw AI predictions dict
            context: Weather + Maps context dict
            gemini_reasoning: Gemini AI reasoning dict (or None for fallback)
            metadata: Tire / vehicle metadata from request

        Returns:
            Complete report dict ready for API response and DB storage
        """
        # Extract core metrics for risk calculation
        tread_info = prediction_result.get("tread_depths_mm", {})
        avg_tread = tread_info.get("average", 5.0)
        health = prediction_result.get("health_score", 5.0)
        remaining_km = prediction_result.get("remaining_life_km", 40000.0)
        wear = prediction_result.get("wear_pattern", {})
        wear_severity = wear.get("severity", "low")

        # Compute overall risk level
        risk_level = compute_risk_level(health, avg_tread, remaining_km, wear_severity)

        # Apply context risk multipliers to remaining life
        road_mult = context.get("road_wear_multiplier", 1.0)
        weather_mult = context.get("weather_risk_multiplier", 1.0)
        combined_mult = road_mult * weather_mult
        adjusted_remaining_km = max(0.0, remaining_km / combined_mult)

        # Use Gemini reasoning or rule-based fallback
        reasoning = gemini_reasoning or _rule_based_reasoning(prediction_result, risk_level)

        # Override risk level from Gemini if available
        if gemini_reasoning and gemini_reasoning.get("risk_level"):
            risk_level = gemini_reasoning["risk_level"]

        # Determine replacement status
        replace_now = (
            avg_tread < 1.6
            or risk_level == "CRITICAL"
            or reasoning.get("replacement_urgency") == "immediate"
        )

        # Generate alerts
        alerts = _generate_alerts(prediction_result, risk_level)

        report_metadata = dict(metadata or {})
        diagnostics = {
            key: prediction_result.get(key)
            for key in (
                "tread_sequence_source",
                "runtime_tread_sequence_mm",
                "condition_prediction",
                "condition_probabilities",
                "depth_derived_wear_pattern",
                "model_wear_pattern_before_depth_override",
                "side_wall_wear_rule",
                "temporal_features",
                "tabular_crosscheck",
                "legacy_classification",
                "context_vector",
            )
            if prediction_result.get(key) is not None
        }
        if diagnostics:
            report_metadata["model_diagnostics"] = diagnostics

        # Build final report
        report = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model_version": prediction_result.get("model_version", MODEL_VERSION),
            "risk_level": risk_level,
            "status": self._status_message(risk_level, avg_tread),
            "replace_immediately": replace_now,
            "confidence": prediction_result.get("confidence", 0.75),
            "predictions": {
                "tread_depths_mm": tread_info,
                "health_score": health,
                "remaining_life_km": round(adjusted_remaining_km, 0),
                "remaining_life_km_raw": round(remaining_km, 0),
                "wear_pattern": wear,
            },
            "context": {
                "terrain_type": context.get("terrain_type"),
                "road_condition": context.get("road_condition"),
                "traffic_density": context.get("traffic_density"),
                "weather_condition": context.get("weather_condition"),
                "temperature_c": context.get("temperature_c"),
                "humidity_pct": context.get("humidity_pct"),
                "visibility_km": context.get("visibility_km"),
                "rain_detected": context.get("rain_detected", False),
                "road_wear_multiplier": road_mult,
                "weather_risk_multiplier": weather_mult,
                "road_condition_basis": context.get("road_condition_basis"),
                "route_source_latitude": context.get("route_source_latitude"),
                "route_source_longitude": context.get("route_source_longitude"),
                "route_destination_latitude": context.get("route_destination_latitude"),
                "route_destination_longitude": context.get("route_destination_longitude"),
                "route_distance_km": context.get("route_distance_km"),
                "route_duration_min": context.get("route_duration_min"),
                "route_analysis_source": context.get("route_analysis_source"),
                "street_view_available": context.get("street_view_available"),
                "street_view_sample_count": context.get("street_view_sample_count"),
                "street_view_covered_samples": context.get("street_view_covered_samples"),
                "street_view_visual_summary": context.get("street_view_visual_summary"),
                "street_view_samples": context.get("street_view_samples"),
            },
            "reasoning": reasoning,
            "alerts": alerts,
            "metadata": report_metadata,
            "blur_score": prediction_result.get("blur_score"),
            "source": prediction_result.get("source", "model"),
        }
        return report

    def _status_message(self, risk_level: str, avg_tread_mm: float) -> str:
        if avg_tread_mm < 1.6:
            return "UNSAFE — Below legal minimum tread depth"
        if risk_level == "CRITICAL":
            return "CRITICAL — Immediate attention required"
        if risk_level == "HIGH":
            return "WARNING — Replace tires soon"
        if risk_level == "MODERATE":
            return "CAUTION — Monitor tire condition"
        return "ACCEPTABLE — Continue normal monitoring"
