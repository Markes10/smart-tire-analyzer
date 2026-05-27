"""
Terrain Analyzer — Classifies terrain type from elevation data
and estimates its impact on tire wear rate.
"""

import logging
from typing import Dict, Optional
from api_integrations.google_maps.maps_client import get_maps_client

logger = logging.getLogger(__name__)

# Elevation-based terrain classification thresholds (meters)
TERRAIN_THRESHOLDS = [
    (0,    100,  "flat",          1.00),
    (100,  500,  "hilly",         1.15),
    (500,  1500, "mountainous",   1.30),
    (1500, 9999, "high_altitude", 1.25),
]

# Road type → wear multiplier mapping
ROAD_TYPE_MULTIPLIERS: Dict[str, float] = {
    "highway":     1.05,   # Fast but smooth
    "urban":       1.20,   # Stop-start + potholes
    "residential": 1.10,
    "rural":       1.15,
    "unpaved":     1.50,
    "gravel":      1.40,
    "cobblestone": 1.30,
    "unknown":     1.10,
}


async def analyze_terrain(lat: float, lon: float) -> Dict:
    """
    Analyze terrain type and road classification for a GPS coordinate.

    Returns:
        Dict with terrain_type, elevation_m, road_type, wear_multiplier
    """
    client = get_maps_client()
    if not client.is_available():
        return _default_terrain()

    # Fetch elevation
    elevation = await client.get_elevation(lat, lon)
    terrain_type, wear_mult = _classify_terrain(elevation)

    # Fetch road type via reverse geocode
    geocode_result = await client.reverse_geocode(lat, lon)
    road_type = _infer_road_type(geocode_result)

    # Snap to road (confirms we're on a navigable road)
    snapped = await client.snap_to_road(lat, lon)
    on_road = snapped is not None

    road_multiplier = ROAD_TYPE_MULTIPLIERS.get(road_type, 1.10)

    return {
        "terrain_type": terrain_type,
        "elevation_m": round(elevation, 1) if elevation is not None else None,
        "road_type": road_type,
        "on_navigable_road": on_road,
        "terrain_wear_multiplier": wear_mult,
        "road_wear_multiplier": road_multiplier,
    }


def _classify_terrain(elevation_m: Optional[float]) -> tuple:
    """Classify terrain from elevation value. Returns (terrain_name, multiplier)."""
    if elevation_m is None:
        return "unknown", 1.0
    for low, high, name, mult in TERRAIN_THRESHOLDS:
        if low <= elevation_m < high:
            return name, mult
    return "high_altitude", 1.25


def _infer_road_type(geocode_result: Optional[Dict]) -> str:
    """
    Infer road type from Google Geocode result address components.
    """
    if not geocode_result:
        return "unknown"

    types = geocode_result.get("types", [])
    address_components = geocode_result.get("address_components", [])

    # Check geocode types
    if "route" in types:
        # Check road name for highway indicators
        for comp in address_components:
            name = comp.get("long_name", "").lower()
            if any(x in name for x in ["highway", "motorway", "expressway", "freeway"]):
                return "highway"
            if any(x in name for x in ["street", "road", "avenue", "lane"]):
                return "urban"
    if "premise" in types or "establishment" in types:
        return "residential"
    return "urban"


def _default_terrain() -> Dict:
    return {
        "terrain_type": "unknown",
        "elevation_m": None,
        "road_type": "unknown",
        "on_navigable_road": None,
        "terrain_wear_multiplier": 1.0,
        "road_wear_multiplier": 1.0,
    }
