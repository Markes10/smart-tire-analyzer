"""
Risk Scorer — Combines weather factors into an overall driving risk multiplier.
Quantifies how weather conditions affect tire safety and wear rate.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Weather condition → base risk modifier
CONDITION_RISK: Dict[str, float] = {
    "Clear":        1.00,
    "Clouds":       1.02,
    "Drizzle":      1.15,
    "Rain":         1.30,
    "Thunderstorm": 1.60,
    "Snow":         1.80,
    "Sleet":        1.70,
    "Mist":         1.10,
    "Fog":          1.25,
    "Haze":         1.05,
    "Dust":         1.15,
    "Sand":         1.20,
    "Ash":          1.25,
    "Tornado":      2.50,
}

# Rain intensity → additional modifier
RAIN_INTENSITY_RISK: Dict[str, float] = {
    "none":     0.00,
    "light":    0.10,
    "moderate": 0.25,
    "heavy":    0.50,
}


def compute_weather_risk(weather_data: Dict) -> Dict:
    """
    Compute comprehensive weather-based tire risk score.

    Takes parsed weather data and returns:
    - overall_risk_multiplier: combined factor (1.0 = no risk, 2.5 = extreme)
    - driving_risk_level: LOW / MODERATE / HIGH / EXTREME
    - contributing_factors: list of active risk factors
    - wet_road: bool — whether road is likely wet

    Args:
        weather_data: Parsed weather dict from WeatherService._parse_weather()

    Returns:
        Dict with risk assessment
    """
    multiplier = 1.0
    factors = []

    # Base condition risk
    condition = weather_data.get("weather_condition", "Clear")
    base = CONDITION_RISK.get(condition, 1.0)
    if base > 1.0:
        multiplier *= base
        factors.append(f"{condition} conditions (+{(base - 1.0) * 100:.0f}%)")

    # Rain intensity additional risk
    rain_intensity = weather_data.get("rain_intensity", "none")
    rain_add = RAIN_INTENSITY_RISK.get(rain_intensity, 0.0)
    if rain_add > 0:
        multiplier += rain_add
        factors.append(f"{rain_intensity.title()} rain (+{rain_add * 100:.0f}%)")

    # Visibility risk
    visibility_km = weather_data.get("visibility_km")
    if visibility_km is not None:
        if visibility_km < 1.0:
            multiplier += 0.30
            factors.append(f"Very low visibility ({visibility_km}km) (+30%)")
        elif visibility_km < 5.0:
            multiplier += 0.15
            factors.append(f"Reduced visibility ({visibility_km}km) (+15%)")

    # Temperature extremes
    temp_c = weather_data.get("temperature_c")
    if temp_c is not None:
        if temp_c > 45.0:
            multiplier += 0.20
            factors.append(f"Extreme heat ({temp_c}°C) — faster tread wear (+20%)")
        elif temp_c > 35.0:
            multiplier += 0.10
            factors.append(f"High temperature ({temp_c}°C) (+10%)")
        elif temp_c < -10.0:
            multiplier += 0.20
            factors.append(f"Extreme cold ({temp_c}°C) — reduced grip (+20%)")
        elif temp_c < 0.0:
            multiplier += 0.10
            factors.append(f"Freezing temperature (+10%)")

    # Wind speed
    wind_ms = weather_data.get("wind_speed_ms")
    if wind_ms is not None and wind_ms > 15.0:
        multiplier += 0.10
        factors.append(f"High wind speed ({wind_ms}m/s) (+10%)")

    # Cap and classify
    multiplier = round(min(multiplier, 2.5), 3)
    wet_road = weather_data.get("rain_detected", False) or condition in (
        "Rain", "Drizzle", "Thunderstorm", "Snow", "Sleet"
    )

    if multiplier >= 2.0:
        risk_level = "EXTREME"
    elif multiplier >= 1.5:
        risk_level = "HIGH"
    elif multiplier >= 1.2:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return {
        "weather_risk_multiplier": multiplier,
        "driving_risk_level":      risk_level,
        "contributing_factors":    factors,
        "wet_road":                wet_road,
        "stopping_distance_increase_pct": max(0, int((multiplier - 1.0) * 100)),
    }


def adjust_remaining_life(
    remaining_km: float,
    road_multiplier: float = 1.0,
    weather_multiplier: float = 1.0,
) -> Dict:
    """
    Adjust remaining tire life based on road and weather conditions.

    Higher multipliers = faster wear = less remaining life.

    Returns:
        Dict with raw, adjusted, and percentage reduction
    """
    combined = road_multiplier * weather_multiplier
    combined = min(combined, 2.5)  # Cap
    adjusted = max(0.0, remaining_km / combined)
    reduction_pct = round((1.0 - adjusted / max(remaining_km, 1)) * 100, 1)

    return {
        "remaining_life_km_raw":       round(remaining_km, 0),
        "remaining_life_km_adjusted":  round(adjusted, 0),
        "reduction_pct":               reduction_pct,
        "road_multiplier":             road_multiplier,
        "weather_multiplier":          weather_multiplier,
        "combined_multiplier":         round(combined, 3),
    }
