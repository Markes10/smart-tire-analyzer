"""
Prompt builder for Gemini tire safety reasoning prompts.
Constructs structured prompts from tire predictions and context data.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias, cast

PromptMap: TypeAlias = Mapping[str, object]


def _as_mapping(value: object) -> PromptMap:
    """Return a mapping view when the input is dict-like, else an empty mapping."""
    if isinstance(value, Mapping):
        return cast(PromptMap, value)
    return {}


def _get_float(data: PromptMap, key: str, default: float = 0.0) -> float:
    """Read a numeric value from a mapping with safe coercion."""
    value = data.get(key, default)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _get_text(data: PromptMap, key: str, default: str = "") -> str:
    """Read a string value from a mapping with a safe fallback."""
    value = data.get(key, default)
    if value is None:
        return default
    return str(value)


def _get_bool(data: PromptMap, key: str, default: bool = False) -> bool:
    """Read a boolean-like value from a mapping with light normalization."""
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "detected"}
    return default


def build_tire_reasoning_prompt(
    predictions: PromptMap,
    context: PromptMap | None = None,
    include_examples: bool = True,
) -> str:
    """
    Build a detailed Gemini reasoning prompt for tire analysis.

    Combines:
    - Tread depth measurements (T1-T4)
    - Health score and remaining life
    - Wear pattern classification
    - Weather and road conditions
    - GPS/environment context
    """
    tread = _as_mapping(predictions.get("tread_depths_mm"))
    wear = _as_mapping(predictions.get("wear_pattern"))
    ctx: PromptMap = context if context is not None else {}

    average_tread = _get_float(tread, "average")
    tread_1 = _get_float(tread, "tread_1")
    tread_2 = _get_float(tread, "tread_2")
    tread_3 = _get_float(tread, "tread_3")
    tread_4 = _get_float(tread, "tread_4")
    tread_min = _get_float(tread, "min")
    tread_max = _get_float(tread, "max")
    health_score = _get_float(predictions, "health_score")
    remaining_life_km = _get_float(predictions, "remaining_life_km")

    wear_label = _get_text(wear, "label", "unknown").replace("_", " ").title()
    wear_cause = _get_text(wear, "cause", "unknown")
    wear_severity = _get_text(wear, "severity", "unknown").upper()
    wear_confidence = _get_float(wear, "confidence")

    tread_section = f"""
## Tire Measurements:
- Average Tread Depth: {average_tread:.1f}mm
  (Legal minimum: 1.6mm | Replacement threshold: 3.0mm | New tire: ~8mm)
- Individual Treads:
  T1 (inner): {tread_1:.1f}mm
  T2 (inner-center): {tread_2:.1f}mm
  T3 (outer-center): {tread_3:.1f}mm
  T4 (outer): {tread_4:.1f}mm
- Tread Differential: {(tread_max - tread_min):.1f}mm
- Tire Health Score: {health_score:.1f}/10
- Estimated Remaining Life: {remaining_life_km:.0f} km"""

    wear_section = f"""
## Wear Pattern Analysis:
- Pattern Type: {wear_label}
- Root Cause: {wear_cause}
- Severity: {wear_severity}
- Detection Confidence: {wear_confidence:.0%}"""

    weather_parts: list[str] = []
    weather_condition = _get_text(ctx, "weather_condition")
    if weather_condition:
        weather_parts.append(f"Condition: {weather_condition}")

    temperature_c = ctx.get("temperature_c")
    if temperature_c is not None:
        weather_parts.append(f"Temperature: {_get_float(ctx, 'temperature_c')}\u00b0C")

    humidity_pct = ctx.get("humidity_pct")
    if humidity_pct is not None:
        weather_parts.append(f"Humidity: {_get_float(ctx, 'humidity_pct')}%")

    visibility_km = ctx.get("visibility_km")
    if visibility_km is not None:
        weather_parts.append(f"Visibility: {_get_float(ctx, 'visibility_km')} km")

    if _get_bool(ctx, "rain_detected"):
        rain_intensity = _get_text(ctx, "rain_intensity", "detected")
        weather_parts.append(f"Rain: {rain_intensity}")

    weather_section = ""
    if weather_parts:
        weather_section = "\n## Current Weather:\n- " + "\n- ".join(weather_parts)

    road_parts: list[str] = []
    terrain_type = _get_text(ctx, "terrain_type")
    if terrain_type:
        road_parts.append(f"Terrain: {terrain_type}")

    road_condition = _get_text(ctx, "road_condition")
    if road_condition:
        road_parts.append(f"Road surface: {road_condition}")

    traffic_density = _get_text(ctx, "traffic_density")
    if traffic_density:
        road_parts.append(f"Traffic: {traffic_density}")

    road_section = ""
    if road_parts:
        road_section = "\n## Road Context:\n- " + "\n- ".join(road_parts)

    example_section = ""
    if include_examples:
        example_section = """
## Example Output Format:
{
  "risk_level": "HIGH",
  "driving_advice": "Reduce highway speed to below 100 km/h. Increase following distance in wet conditions.",
  "replacement_recommended": true,
  "replacement_urgency": "within_1000km",
  "primary_cause": "Underinflation",
  "additional_notes": "Check tire pressure immediately. Front-rear rotation may not be recommended given uneven wear.",
  "safety_score": 35
}"""

    prompt = f"""You are a certified tire safety engineer analyzing real-world tire condition data.
Your assessment directly impacts driver safety. Be precise, practical, and safety-first.
{tread_section}
{wear_section}
{weather_section}
{road_section}
{example_section}

## Your Task:
Analyze the above tire condition data and provide a comprehensive safety assessment.
Consider the interaction between wear pattern, remaining tread depth, and environmental conditions.

Respond ONLY with valid JSON in exactly this format:
{{
  "risk_level": "<CRITICAL|HIGH|MODERATE|LOW>",
  "driving_advice": "<specific 1-2 sentence actionable advice>",
  "replacement_recommended": <true|false>,
  "replacement_urgency": "<immediate|within_1000km|within_5000km|monitor>",
  "primary_cause": "<root cause of tire condition>",
  "additional_notes": "<optional corrective actions or warnings>",
  "safety_score": <0-100 integer, 100=perfect, 0=dangerous>
}}"""

    return prompt


def build_anomaly_detection_prompt(
    image_features: PromptMap,
    confidence: float,
) -> str:
    """
    Build a prompt for detecting unusual or anomalous tire conditions.
    """
    return f"""You are a tire safety expert reviewing an AI analysis result.

The model detected an unusual tire condition:
- Model confidence: {confidence:.0%} (low confidence suggests anomaly)
- Detected features: {dict(image_features)}

Does this suggest a tire defect, sidewall bulge, cracking, or other non-wear damage?
Respond in JSON: {{"is_anomaly": true/false, "anomaly_type": "...", "urgency": "..."}}"""
