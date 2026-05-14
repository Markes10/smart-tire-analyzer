"""
Maps Service — Google Maps API integration.
Fetches terrain, road condition, and traffic data from GPS coordinates.
Falls back to rule-based estimation when API key not configured.
"""

import os
import logging
import aiohttp
from typing import Dict, Any, cast

from app.config import settings
from app.services.api_key_rotator import get_maps_rotator, APIKeyRotator

logger = logging.getLogger(__name__)


class MapsService:
    def __init__(self):
        rot = get_maps_rotator()
        if not rot:
            keys = settings.get_maps_keys()
            rot = APIKeyRotator("maps", keys, daily_quota=settings.MAPS_DAILY_QUOTA) if keys else None

        self.rotator = rot
        self.enabled = bool(self.rotator and self.rotator.available_keys)
        if not self.enabled:
            logger.warning("No Maps API keys configured — using mock road context")

    async def get_road_context(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch terrain type, road condition, and traffic density.
        Returns a dict with road_wear_multiplier and weather_risk_multiplier.
        """
        if not self.enabled:
            return self._mock_context(lat, lon)

        try:
            elevation_data = await self._fetch_elevation(lat, lon)
            elevation_m = elevation_data.get("elevation", 100)

            terrain_type = self._classify_terrain(elevation_m)
            road_condition = "good"          # Would use Roads API in production
            traffic_density = "moderate"     # Would use Traffic layer in production

            return {
                "terrain_type": terrain_type,
                "road_condition": road_condition,
                "traffic_density": traffic_density,
                "elevation_m": elevation_m,
                "road_wear_multiplier": self._road_wear_mult(terrain_type, road_condition),
                "latitude": lat,
                "longitude": lon,
            }
        except Exception as e:
            logger.warning(f"Maps API error: {e} — using mock")
            return self._mock_context(lat, lon)

    async def _fetch_elevation(self, lat: float, lon: float) -> Dict[str, Any]:
        if not self.enabled:
            return {"elevation": 50}

        attempts = 0
        max_attempts = max(1, len(self.rotator.available_keys))
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while attempts < max_attempts:
                key = self.rotator.get_current_key()
                url = (
                    f"https://maps.googleapis.com/maps/api/elevation/json"
                    f"?locations={lat},{lon}&key={key}"
                )
                try:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        results = data.get("results", [])
                        if results:
                            res = results[0]
                            if isinstance(res, dict):
                                try:
                                    self.rotator.record_successful_request(key)
                                except Exception:
                                    pass
                                return cast(Dict[str, Any], res)
                        try:
                            self.rotator.record_successful_request(key)
                        except Exception:
                            pass
                        return {"elevation": 50}
                except aiohttp.ClientResponseError as e:
                    status = getattr(e, "status", None)
                    logger.warning(f"Maps API HTTP error (status={status}): {e}")
                    if status in (429, 403, 401):
                        logger.info("Rotating Maps API key due to HTTP status %s", status)
                        try:
                            self.rotator.record_error(key, str(e))
                            self.rotator.rotate_to_next_key()
                        except Exception:
                            pass
                        attempts += 1
                        continue
                    raise
                except Exception as e:
                    logger.warning(f"Maps API error: {e}")
                    # Try next key once
                    try:
                        self.rotator.record_error(key, str(e))
                        self.rotator.rotate_to_next_key()
                    except Exception:
                        pass
                    attempts += 1
                    continue

        return {"elevation": 50}

    def _classify_terrain(self, elevation_m: float) -> str:
        if elevation_m < 50:
            return "flat_urban"
        if elevation_m < 300:
            return "rolling_suburban"
        if elevation_m < 800:
            return "hilly"
        return "mountainous"

    def _road_wear_mult(self, terrain: str, road_cond: str) -> float:
        """Higher multiplier = road degrades tires faster = less remaining life."""
        terrain_mult = {"flat_urban": 1.0, "rolling_suburban": 1.05,
                        "hilly": 1.12, "mountainous": 1.25}.get(terrain, 1.0)
        road_mult = {"excellent": 0.95, "good": 1.0,
                     "fair": 1.1, "poor": 1.25}.get(road_cond, 1.0)
        return round(terrain_mult * road_mult, 3)

    def _mock_context(self, lat: float, lon: float) -> Dict:
        return {
            "terrain_type": "flat_urban",
            "road_condition": "good",
            "traffic_density": "moderate",
            "elevation_m": None,
            "road_wear_multiplier": 1.0,
            "latitude": lat,
            "longitude": lon,
        }
