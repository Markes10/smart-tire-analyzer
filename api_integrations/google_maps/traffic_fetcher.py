"""
Traffic Fetcher — Estimates traffic density and its impact on tire wear.
Uses Google Maps Distance Matrix API heuristics.
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Hour-of-day → typical traffic density mapping (urban estimate)
HOURLY_TRAFFIC = {
    range(0, 6):   "low",        # Midnight–6am: quiet
    range(6, 9):   "heavy",      # Morning rush
    range(9, 12):  "moderate",
    range(12, 14): "moderate",   # Lunch
    range(14, 17): "moderate",
    range(17, 20): "heavy",      # Evening rush
    range(20, 24): "low",
}

# Traffic density → tire wear multiplier
TRAFFIC_MULTIPLIERS = {
    "low":       1.00,
    "moderate":  1.08,
    "heavy":     1.20,
    "congested": 1.35,
}


def estimate_traffic_density(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict:
    """
    Estimate current traffic density.

    Uses:
    1. Hour-of-day heuristic (always available)
    2. Day-of-week adjustment (weekday vs weekend)

    In production: replace with Google Maps Distance Matrix API
    with departure_time=now for real-time traffic.

    Returns:
        Dict with traffic_density, traffic_multiplier, method
    """
    now = datetime.now()
    hour = now.hour
    is_weekday = now.weekday() < 5  # Mon–Fri

    # Get base density from hour
    density = "moderate"
    for hour_range, lvl in HOURLY_TRAFFIC.items():
        if hour in hour_range:
            density = lvl
            break

    # Weekends have lighter traffic
    if not is_weekday and density == "heavy":
        density = "moderate"

    multiplier = TRAFFIC_MULTIPLIERS.get(density, 1.0)

    return {
        "traffic_density":    density,
        "traffic_multiplier": multiplier,
        "traffic_method":     "time_heuristic",
        "is_peak_hour":       density == "heavy",
        "hour_of_day":        hour,
        "is_weekday":         is_weekday,
    }


def combined_road_wear_multiplier(
    terrain_multiplier: float = 1.0,
    road_multiplier: float = 1.0,
    traffic_multiplier: float = 1.0,
) -> float:
    """
    Combine terrain + road + traffic multipliers into single wear factor.
    Capped at 2.5× to prevent unrealistic estimates.
    """
    combined = terrain_multiplier * road_multiplier * traffic_multiplier
    return round(min(combined, 2.5), 3)
