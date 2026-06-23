"""
ANN output utilities for Smart Tire Analyzer.

This module bridges raw model outputs and the report-shaped dictionaries used
by the API, local scripts, and tests.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np

from ai_model.classes import (
    DrivingRiskClass,
    ModelConfidenceClass,
    TreadDepthClass,
    WearPatternClass,
    advice_from_risk,
    classify_confidence,
    classify_health,
    classify_tread_depth,
)
from ai_model.rnn.sequence_builder import normalize_tread_depths

logger = logging.getLogger(__name__)

TREAD_MAX_MM = 12.0
HEALTH_SCORE_MAX = 10.0
MAX_REMAINING_KM = 80000.0

CRITICAL_TREAD = 1.6
HIGH_TREAD = 3.0
MODERATE_TREAD = 5.0

CRITICAL_HEALTH = 2.0
HIGH_HEALTH = 4.0
MODERATE_HEALTH = 6.0

WEAR_PATTERN_INDEX_TO_LABEL = [
    "center_wear",
    "edge_wear",
    "patchy_wear",
    "uniform_wear",
    "one_side_wear",
    "cupping_wear",
]

WEAR_ALIAS_TO_CLASS: dict[str, WearPatternClass] = {
    "center_wear": WearPatternClass.CENTER_WEAR,
    "edge_wear": WearPatternClass.EDGE_WEAR,
    "patchy_wear": WearPatternClass.PATCH_WEAR,
    "patch_wear": WearPatternClass.PATCH_WEAR,
    "uniform_wear": WearPatternClass.EVEN_WEAR,
    "even_wear": WearPatternClass.EVEN_WEAR,
    "one_side_wear": WearPatternClass.ONE_SIDE_WEAR,
    "one_sided_wear": WearPatternClass.ONE_SIDE_WEAR,
    "cupping_wear": WearPatternClass.CUPPING_WEAR,
    "feathering_wear": WearPatternClass.FEATHERING_WEAR,
}

CLASS_TO_CANONICAL_WEAR_LABEL: dict[WearPatternClass, str] = {
    WearPatternClass.CENTER_WEAR: "center_wear",
    WearPatternClass.EDGE_WEAR: "edge_wear",
    WearPatternClass.PATCH_WEAR: "patchy_wear",
    WearPatternClass.EVEN_WEAR: "uniform_wear",
    WearPatternClass.ONE_SIDE_WEAR: "one_side_wear",
    WearPatternClass.CUPPING_WEAR: "cupping_wear",
    WearPatternClass.FEATHERING_WEAR: "patchy_wear",
}

SIDE_WALL_WEAR_LABEL = "side_wall_wear"
SIDE_WALL_WEAR_DISPLAY = "Side-Wall Wear"
SIDE_WALL_WEAR_CAUSE = "Outer shoulder wear concentrated on the tire edge"
SIDE_WALL_WEAR_ADVICE = "Inspect wheel alignment, camber, and the outer shoulder before continued use."


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        array = _as_numpy(value)
        if array.size == 0:
            return default
        return float(array.reshape(-1)[0])
    except Exception:
        try:
            return float(value)
        except Exception:
            return default


def _flatten_float_array(value: Any) -> np.ndarray:
    array = _as_numpy(value).astype(np.float32, copy=False)
    return array.reshape(-1)


def _looks_normalized(values: np.ndarray, max_value: float) -> bool:
    if values.size == 0:
        return False
    min_value = float(np.min(values))
    max_seen = float(np.max(values))
    return min_value >= -0.05 and max_seen <= 1.05 and max_value > 1.0


def _maybe_scale(values: np.ndarray, max_value: float) -> np.ndarray:
    if _looks_normalized(values, max_value):
        return values * max_value
    return values


def _resolve_wear_class(label: str) -> WearPatternClass:
    canonical = WEAR_ALIAS_TO_CLASS.get(label, WearPatternClass.EVEN_WEAR)
    return canonical


def _canonical_wear_label(label: str) -> str:
    if label == SIDE_WALL_WEAR_LABEL:
        return SIDE_WALL_WEAR_LABEL
    return CLASS_TO_CANONICAL_WEAR_LABEL[_resolve_wear_class(label)]


def _wear_probabilities(probabilities: np.ndarray) -> dict[str, float]:
    flat = probabilities.reshape(-1)
    if flat.size == 0:
        return {"uniform_wear": 1.0}

    label_count = min(len(WEAR_PATTERN_INDEX_TO_LABEL), flat.size)
    probs = flat[:label_count].astype(np.float32, copy=False)
    total = float(np.sum(probs))
    if total > 0:
        probs = probs / total

    return {
        WEAR_PATTERN_INDEX_TO_LABEL[index]: round(float(prob), 4)
        for index, prob in enumerate(probs)
    }


def _infer_wear_pattern_from_depths(depths: list[float] | np.ndarray) -> str:
    depth_array = np.asarray(depths, dtype=np.float32)
    diff = float(np.max(depth_array) - np.min(depth_array))
    inner = float(depth_array[0])
    outer = float(depth_array[-1])
    center_avg = float(np.mean(depth_array[1:3]))

    if outer - inner > 0.8 and outer / max(inner, 0.01) > 1.5:
        return SIDE_WALL_WEAR_LABEL
    if diff < 0.5:
        return "uniform_wear"
    if center_avg < outer - 0.8:
        return "center_wear"
    if inner < center_avg - 0.8:
        return "edge_wear"
    if (inner - outer) > 1.5:
        return "one_side_wear"
    if diff > 2.0:
        return "patchy_wear"
    return "patchy_wear"


def _classify_tread_status(avg_tread_mm: float) -> str:
    """Legacy tread status helper retained for compatibility."""
    if avg_tread_mm < CRITICAL_TREAD:
        return "ILLEGAL"
    if avg_tread_mm < HIGH_TREAD:
        return "CRITICAL"
    if avg_tread_mm < MODERATE_TREAD:
        return "WARNING"
    if avg_tread_mm < 7.0:
        return "ACCEPTABLE"
    return "GOOD"


def compute_risk_level(
    health: float | None = None,
    avg_tread_mm: float = 5.0,
    remaining_km: float = 40000.0,
    wear_severity: str = "low",
    *,
    health_score: float | None = None,
) -> str:
    """
    Compute the overall tire risk level.

    Supports both the newer ``health`` argument and the older
    ``health_score=...`` call sites.
    """
    health_value = health_score if health_score is not None else health
    if health_value is None:
        health_value = 5.0

    wear_critical = wear_severity in {"critical", "high"}

    if avg_tread_mm < CRITICAL_TREAD or health_value < CRITICAL_HEALTH or wear_critical:
        return DrivingRiskClass.CRITICAL.api_value
    if avg_tread_mm < HIGH_TREAD or health_value < HIGH_HEALTH or remaining_km < 5_000:
        return DrivingRiskClass.HIGH.api_value
    if avg_tread_mm < MODERATE_TREAD or health_value < MODERATE_HEALTH or remaining_km < 20_000:
        return DrivingRiskClass.MODERATE.api_value
    return DrivingRiskClass.LOW.api_value


def _wear_severity_from_depths(wear_label: str, tread_stats: dict[str, float]) -> str:
    differential = float(tread_stats.get("differential", 0.0))
    average = float(tread_stats.get("average", 5.0))

    if average < CRITICAL_TREAD or differential >= 3.0:
        return "critical"
    if average < HIGH_TREAD or differential >= 2.0:
        return "high"
    if wear_label != "uniform_wear" and (average < MODERATE_TREAD or differential >= 1.0):
        return "moderate"
    return "low"


def denormalize_outputs(
    raw_outputs: dict[str, Any],
    *,
    confidence_override: float | None = None,
    source: str = "model",
) -> dict[str, Any]:
    """
    Convert raw model outputs into the canonical prediction dictionary.

    If ``raw_outputs`` is already in report-friendly prediction format, it is
    returned with light normalization only.
    """
    if "tread_depths_mm" in raw_outputs and "wear_pattern" in raw_outputs:
        prediction = dict(raw_outputs)
        prediction["confidence"] = float(
            np.clip(confidence_override if confidence_override is not None else prediction.get("confidence", 0.75), 0.0, 1.0)
        )
        prediction.setdefault("source", source)
        wear = dict(prediction.get("wear_pattern", {}))
        wear["label"] = _canonical_wear_label(wear.get("label", "uniform_wear"))
        if wear["label"] == SIDE_WALL_WEAR_LABEL:
            wear.setdefault("label_display", SIDE_WALL_WEAR_DISPLAY)
            wear.setdefault("cause", SIDE_WALL_WEAR_CAUSE)
            wear.setdefault("advice", SIDE_WALL_WEAR_ADVICE)
        else:
            wear_class = _resolve_wear_class(wear["label"])
            wear.setdefault("label_display", wear_class.label)
            wear.setdefault("cause", wear_class.cause)
            wear.setdefault("advice", wear_class.advice)
        wear.setdefault("severity", _wear_severity_from_depths(wear["label"], prediction["tread_depths_mm"]))
        wear.setdefault("confidence", prediction["confidence"])
        prediction["wear_pattern"] = wear
        return prediction

    tread_values = _flatten_float_array(raw_outputs.get("tread_depths", [5.0, 5.0, 5.0, 5.0]))
    if tread_values.size == 0:
        tread_values = np.asarray([5.0, 5.0, 5.0, 5.0], dtype=np.float32)
    if tread_values.size == 1:
        tread_values = np.repeat(tread_values, 4)
    tread_mm = _maybe_scale(tread_values[:4], TREAD_MAX_MM)
    tread_stats = normalize_tread_depths(tread_mm.tolist())

    health_score = _as_float(raw_outputs.get("health_score", 0.5))
    if 0.0 <= health_score <= 1.05:
        health_score *= HEALTH_SCORE_MAX
    health_score = float(np.clip(health_score, 0.0, HEALTH_SCORE_MAX))

    remaining_life = _as_float(raw_outputs.get("remaining_life", 0.5))
    if 0.0 <= remaining_life <= 1.05:
        remaining_life *= MAX_REMAINING_KM
    remaining_life = float(np.clip(remaining_life, 0.0, MAX_REMAINING_KM))

    wear_output = raw_outputs.get("wear_pattern")
    wear_probs = _flatten_float_array(wear_output) if wear_output is not None else np.asarray([], dtype=np.float32)
    if wear_probs.size >= 1:
        wear_index = int(np.argmax(wear_probs[: len(WEAR_PATTERN_INDEX_TO_LABEL)]))
        wear_label = WEAR_PATTERN_INDEX_TO_LABEL[wear_index]
        wear_confidence = float(np.max(wear_probs))
    else:
        wear_label = _infer_wear_pattern_from_depths(tread_mm.tolist())
        wear_confidence = 0.72

    wear_label = _canonical_wear_label(wear_label)
    wear_class = None if wear_label == SIDE_WALL_WEAR_LABEL else _resolve_wear_class(wear_label)
    wear_severity = _wear_severity_from_depths(wear_label, tread_stats)

    confidence = float(
        np.clip(
            confidence_override if confidence_override is not None else wear_confidence,
            0.0,
            1.0,
        )
    )

    tread_average = float(tread_stats["average"])
    tread_class = _classify_tread_status(tread_average)
    health_class = classify_health(health_score)
    confidence_class = classify_confidence(confidence)

    return {
        "tread_depths_mm": {
            "tread_1": round(float(tread_stats["tread_1"]), 2),
            "tread_2": round(float(tread_stats["tread_2"]), 2),
            "tread_3": round(float(tread_stats["tread_3"]), 2),
            "tread_4": round(float(tread_stats["tread_4"]), 2),
            "average": round(tread_average, 2),
            "min": round(float(tread_stats["min"]), 2),
            "max": round(float(tread_stats["max"]), 2),
        },
        "health_score": round(health_score, 1),
        "tire_condition_class": health_class.label,
        "tread_class": tread_class,
        "remaining_life_km": round(remaining_life, 0),
        "wear_pattern": {
            "class_id": -1 if wear_label == SIDE_WALL_WEAR_LABEL else WEAR_PATTERN_INDEX_TO_LABEL.index(wear_label),
            "label": wear_label,
            "label_display": SIDE_WALL_WEAR_DISPLAY if wear_label == SIDE_WALL_WEAR_LABEL else wear_class.label,
            "cause": SIDE_WALL_WEAR_CAUSE if wear_label == SIDE_WALL_WEAR_LABEL else wear_class.cause,
            "advice": SIDE_WALL_WEAR_ADVICE if wear_label == SIDE_WALL_WEAR_LABEL else wear_class.advice,
            "severity": wear_severity,
            "confidence": round(confidence, 4),
            "probabilities": _wear_probabilities(wear_probs),
        },
        "confidence": round(confidence, 4),
        "confidence_class": confidence_class.label,
        "source": source,
    }


def enrich_prediction_with_classes(prediction: dict[str, Any]) -> dict[str, Any]:
    """Attach class labels and advice to a prediction dictionary."""
    health_score = float(prediction.get("health_score", 5.0))
    tread_avg = float(prediction.get("tread_depths_mm", {}).get("average", 5.0))
    wear_label = _canonical_wear_label(prediction.get("wear_pattern", {}).get("label", "uniform_wear"))
    confidence = float(prediction.get("confidence", 0.75))

    health_class = classify_health(health_score)
    tread_class = classify_tread_depth(tread_avg)
    wear_class = _resolve_wear_class(wear_label)
    confidence_class = classify_confidence(confidence)
    risk_level = prediction.get(
        "risk_level",
        compute_risk_level(health_score=health_score, avg_tread_mm=tread_avg, remaining_km=prediction.get("remaining_life_km", 0.0), wear_severity=prediction.get("wear_pattern", {}).get("severity", "low")),
    )
    risk_class = DrivingRiskClass[risk_level]

    prediction["tire_condition_class"] = health_class.label
    prediction["tread_depth_class"] = tread_class.label
    if wear_label == SIDE_WALL_WEAR_LABEL:
        prediction["wear_pattern_class"] = {
            "label": SIDE_WALL_WEAR_DISPLAY,
            "cause": SIDE_WALL_WEAR_CAUSE,
            "advice": SIDE_WALL_WEAR_ADVICE,
        }
    else:
        prediction["wear_pattern_class"] = {
            "label": wear_class.label,
            "cause": wear_class.cause,
            "advice": wear_class.advice,
        }
    prediction["confidence_class"] = confidence_class.label
    prediction["advice"] = [advice.label for advice in advice_from_risk(risk_class)]
    return prediction


def _generate_alerts(predictions: dict[str, Any], risk_level: str) -> list[dict[str, str]]:
    """Generate user-facing alerts from prediction data."""
    alerts: list[dict[str, str]] = []
    tread = predictions.get("tread_depths_mm", {})
    wear = predictions.get("wear_pattern", {})
    avg_tread = float(tread.get("average", 5.0))
    min_tread = float(tread.get("min", avg_tread))
    max_tread = float(tread.get("max", avg_tread))
    differential = max_tread - min_tread

    tread_class = classify_tread_depth(min_tread)
    if min_tread < CRITICAL_TREAD or tread_class == TreadDepthClass.DANGEROUS:
        alerts.append(
            {
                "level": DrivingRiskClass.CRITICAL.api_value,
                "class": _classify_tread_status(min_tread),
                "message": f"Tread depth {min_tread:.1f}mm is below the legal minimum of 1.6mm.",
            }
        )
    elif min_tread < HIGH_TREAD:
        alerts.append(
            {
                "level": DrivingRiskClass.HIGH.api_value,
                "class": _classify_tread_status(min_tread),
                "message": f"Minimum tread depth {min_tread:.1f}mm is dangerously low.",
            }
        )

    if differential > 2.5:
        alerts.append(
            {
                "level": DrivingRiskClass.HIGH.api_value,
                "class": "Uneven Wear",
                "message": f"Tread depth differential of {differential:.1f}mm indicates severe uneven wear.",
            }
        )
    elif differential > 1.5:
        alerts.append(
            {
                "level": DrivingRiskClass.MODERATE.api_value,
                "class": "Uneven Wear",
                "message": f"Tread depth differential of {differential:.1f}mm suggests alignment should be checked.",
            }
        )

    wear_label = _canonical_wear_label(wear.get("label", "uniform_wear"))
    if wear_label == SIDE_WALL_WEAR_LABEL:
        wear_label_display = SIDE_WALL_WEAR_DISPLAY
        wear_advice = SIDE_WALL_WEAR_ADVICE
    else:
        wear_class = _resolve_wear_class(wear_label)
        wear_label_display = wear_class.label
        wear_advice = wear_class.advice
    wear_severity = wear.get("severity", "low")
    if wear_severity == "critical":
        alerts.append(
            {
                "level": DrivingRiskClass.CRITICAL.api_value,
                "class": wear_label_display,
                "message": f"Critical {wear_label_display.lower()} detected. {wear_advice}",
            }
        )
    elif wear_severity == "high":
        alerts.append(
            {
                "level": DrivingRiskClass.HIGH.api_value,
                "class": wear_label_display,
                "message": f"Severe {wear_label_display.lower()} detected. {wear_advice}",
            }
        )

    if risk_level == DrivingRiskClass.CRITICAL.api_value and not alerts:
        alerts.append(
            {
                "level": DrivingRiskClass.CRITICAL.api_value,
                "class": "Critical Risk",
                "message": "Tire condition is unsafe and requires immediate attention.",
            }
        )

    return alerts


def _rule_based_reasoning(predictions: dict[str, Any], risk_level: str) -> dict[str, Any]:
    """Fallback reasoning when Gemini is unavailable."""
    health = float(predictions.get("health_score", 5.0))
    wear = predictions.get("wear_pattern", {})
    wear_label = _canonical_wear_label(wear.get("label", "uniform_wear"))
    if wear_label == SIDE_WALL_WEAR_LABEL:
        wear_cause = SIDE_WALL_WEAR_CAUSE
        wear_advice = SIDE_WALL_WEAR_ADVICE
    else:
        wear_class = _resolve_wear_class(wear_label)
        wear_cause = wear_class.cause
        wear_advice = wear_class.advice
    risk_class = DrivingRiskClass[risk_level]

    advice_text = {
        DrivingRiskClass.CRITICAL: "Stop driving immediately. Tires are unsafe and should be replaced before next use.",
        DrivingRiskClass.HIGH: "Schedule replacement within 1,000 km and avoid aggressive driving.",
        DrivingRiskClass.MODERATE: "Plan replacement within 5,000 km and inspect tread regularly.",
        DrivingRiskClass.LOW: "Tires are in acceptable condition. Maintain pressure and keep monitoring them.",
    }
    urgency = {
        DrivingRiskClass.CRITICAL: "immediate",
        DrivingRiskClass.HIGH: "within_1000km",
        DrivingRiskClass.MODERATE: "within_5000km",
        DrivingRiskClass.LOW: "monitor",
    }

    return {
        "source": "rule_based",
        "risk_level": risk_class.api_value,
        "driving_advice": advice_text[risk_class],
        "advice_classes": [advice.label for advice in advice_from_risk(risk_class)],
        "replacement_recommended": risk_class in {DrivingRiskClass.CRITICAL, DrivingRiskClass.HIGH},
        "replacement_urgency": urgency[risk_class],
        "primary_cause": wear.get("cause", wear_cause),
        "additional_notes": wear.get("advice", wear_advice),
        "safety_score": int(max(0, min(100, health * 10))),
    }


def _status_message(risk_level: str, avg_tread_mm: float) -> str:
    if avg_tread_mm < CRITICAL_TREAD:
        return "UNSAFE - Below legal minimum tread depth"
    if risk_level == DrivingRiskClass.CRITICAL.api_value:
        return "CRITICAL - Immediate attention required"
    if risk_level == DrivingRiskClass.HIGH.api_value:
        return "WARNING - Replace tires soon"
    if risk_level == DrivingRiskClass.MODERATE.api_value:
        return "CAUTION - Monitor tire condition"
    return "ACCEPTABLE - Continue normal monitoring"


def build_final_report(
    raw_outputs: dict[str, Any],
    *,
    session_id: str = "local-analysis",
    context: dict[str, Any] | None = None,
    reasoning: dict[str, Any] | None = None,
    model_version: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Build the canonical report payload from raw model outputs."""
    predictions = denormalize_outputs(raw_outputs, source=source or raw_outputs.get("source", "model"))

    tread_info = predictions["tread_depths_mm"]
    health = float(predictions.get("health_score", 5.0))
    remaining_km = float(predictions.get("remaining_life_km", 40000.0))
    wear = predictions.get("wear_pattern", {})
    risk_level = compute_risk_level(
        health_score=health,
        avg_tread_mm=float(tread_info.get("average", 5.0)),
        remaining_km=remaining_km,
        wear_severity=wear.get("severity", "low"),
    )

    final_reasoning = reasoning or _rule_based_reasoning(predictions, risk_level)
    if reasoning and reasoning.get("risk_level"):
        risk_level = str(reasoning["risk_level"])

    report_context = context or {}
    road_multiplier = float(report_context.get("road_wear_multiplier", 1.0) or 1.0)
    weather_multiplier = float(report_context.get("weather_risk_multiplier", 1.0) or 1.0)
    combined_multiplier = max(road_multiplier * weather_multiplier, 1e-6)
    adjusted_remaining_km = round(remaining_km / combined_multiplier, 0)

    replace_immediately = (
        float(tread_info.get("average", 5.0)) < CRITICAL_TREAD
        or risk_level == DrivingRiskClass.CRITICAL.api_value
        or final_reasoning.get("replacement_urgency") == "immediate"
    )

    return {
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model_version": model_version or raw_outputs.get("model_version") or "1.0.0",
        "risk_level": risk_level,
        "status": _status_message(risk_level, float(tread_info.get("average", 5.0))),
        "replace_immediately": bool(replace_immediately),
        "confidence": float(predictions.get("confidence", 0.75)),
        "predictions": {
            "tread_depths_mm": tread_info,
            "health_score": round(health, 1),
            "remaining_life_km": adjusted_remaining_km,
            "remaining_life_km_raw": round(remaining_km, 0),
            "wear_pattern": wear,
        },
        "context": {
            "terrain_type": report_context.get("terrain_type"),
            "road_condition": report_context.get("road_condition"),
            "traffic_density": report_context.get("traffic_density"),
            "weather_condition": report_context.get("weather_condition"),
            "temperature_c": report_context.get("temperature_c"),
            "humidity_pct": report_context.get("humidity_pct"),
            "visibility_km": report_context.get("visibility_km"),
            "rain_detected": report_context.get("rain_detected", False),
            "road_wear_multiplier": road_multiplier,
            "weather_risk_multiplier": weather_multiplier,
        },
        "reasoning": final_reasoning,
        "alerts": _generate_alerts(predictions, risk_level),
        "metadata": raw_outputs.get("metadata", {}),
        "blur_score": raw_outputs.get("blur_score"),
        "source": predictions.get("source", source or "model"),
    }
