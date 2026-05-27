"""
Google Maps client for low-level Maps API requests with rotation support.
"""

from __future__ import annotations

import logging
import os
from typing import Any, TypeAlias, Optional

import aiohttp

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "roads": "https://roads.googleapis.com/v1/nearestRoads",
    "elevation": "https://maps.googleapis.com/maps/api/elevation/json",
    "geocode": "https://maps.googleapis.com/maps/api/geocode/json",
    "directions": "https://maps.googleapis.com/maps/api/directions/json",
}

DEFAULT_TIMEOUT = 5

JsonMap: TypeAlias = dict[str, Any]


class MapsClient:
    """
    Low-level Google Maps API HTTP client with rotation support.
    All methods are async and handle network errors gracefully.
    """

    api_key: str
    enabled: bool
    rotator: Optional[Any]

    def __init__(self, api_key: str | None = None, rotator=None) -> None:
        """
        Initialize Maps client.
        
        Args:
            api_key: Single API key (for backward compatibility)
            rotator: APIKeyRotator instance for multi-key rotation
        """
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.rotator = rotator
        self.enabled = bool(self.api_key or (rotator and rotator.available_keys))

    async def _request_with_key(
        self,
        endpoint: str,
        params: JsonMap,
        api_key: str,
    ) -> JsonMap | None:
        """Make a single API request with given key."""
        params_copy = params.copy()
        params_copy["key"] = api_key

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            ) as session:
                async with session.get(endpoint, params=params_copy) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                logger.warning(f"Maps API quota exceeded (429)")
            else:
                logger.warning(f"Maps API HTTP {e.status}: {e.message}")
        except Exception as exc:
            logger.warning("Maps API request error: %s", exc)
        return None

    async def get_elevation(self, lat: float, lon: float) -> float | None:
        """
        Fetch elevation in meters for a GPS coordinate.
        Automatically rotates to next API key on failure or quota exceeded.
        
        Returns None on failure.
        """
        if not self.enabled:
            return None

        params = {
            "locations": f"{lat},{lon}",
        }

        if self.rotator:
            available_keys = self.rotator.available_quota_keys
            if not available_keys:
                logger.error("No Maps API keys with available quota")
                return None

            for attempt, key in enumerate(available_keys):
                data = await self._request_with_key(ENDPOINTS["elevation"], params, key)
                if data is not None:
                    results = data.get("results", [])
                    if isinstance(results, list) and results:
                        first = results[0]
                        if isinstance(first, dict):
                            self.rotator.record_successful_request(key)
                            return float(first.get("elevation", 0.0))
                
                self.rotator.record_error(key, "Elevation request failed")
                if attempt < len(available_keys) - 1:
                    logger.warning("Retrying elevation with next Maps API key...")
                    self.rotator.rotate_to_next_key()
            
            logger.error("All available Maps API keys failed for elevation")
            return None
        else:
            data = await self._request_with_key(ENDPOINTS["elevation"], params, self.api_key)
            if data is not None:
                results = data.get("results", [])
                if isinstance(results, list) and results:
                    first = results[0]
                    if isinstance(first, dict):
                        return float(first.get("elevation", 0.0))
            return None

    async def snap_to_road(self, lat: float, lon: float) -> JsonMap | None:
        """
        Snap a GPS coordinate to the nearest road.
        Automatically rotates to next API key on failure or quota exceeded.
        
        Returns snapped point data or None on failure.
        """
        if not self.enabled:
            return None

        params = {
            "points": f"{lat},{lon}",
        }

        if self.rotator:
            available_keys = self.rotator.available_quota_keys
            if not available_keys:
                logger.error("No Maps API keys with available quota")
                return None

            for attempt, key in enumerate(available_keys):
                data = await self._request_with_key(ENDPOINTS["roads"], params, key)
                if data is not None:
                    snapped = data.get("snappedPoints", [])
                    if isinstance(snapped, list) and snapped:
                        first = snapped[0]
                        if isinstance(first, dict):
                            self.rotator.record_successful_request(key)
                            return first
                
                self.rotator.record_error(key, "Snap to road request failed")
                if attempt < len(available_keys) - 1:
                    logger.warning("Retrying snap to road with next Maps API key...")
                    self.rotator.rotate_to_next_key()
            
            logger.error("All available Maps API keys failed for snap to road")
            return None
        else:
            data = await self._request_with_key(ENDPOINTS["roads"], params, self.api_key)
            if data is not None:
                snapped = data.get("snappedPoints", [])
                if isinstance(snapped, list) and snapped:
                    first = snapped[0]
                    if isinstance(first, dict):
                        return first
            return None

    async def reverse_geocode(self, lat: float, lon: float) -> JsonMap | None:
        """
        Reverse geocode a lat/lon to address and location type.
        Automatically rotates to next API key on failure or quota exceeded.
        """
        if not self.enabled:
            return None

        params = {
            "latlng": f"{lat},{lon}",
        }

        if self.rotator:
            available_keys = self.rotator.available_quota_keys
            if not available_keys:
                logger.error("No Maps API keys with available quota")
                return None

            for attempt, key in enumerate(available_keys):
                data = await self._request_with_key(ENDPOINTS["geocode"], params, key)
                if data is not None:
                    results = data.get("results", [])
                    if isinstance(results, list) and results:
                        first = results[0]
                        if isinstance(first, dict):
                            self.rotator.record_successful_request(key)
                            return first
                
                self.rotator.record_error(key, "Reverse geocode request failed")
                if attempt < len(available_keys) - 1:
                    logger.warning("Retrying reverse geocode with next Maps API key...")
                    self.rotator.rotate_to_next_key()
            
            logger.error("All available Maps API keys failed for reverse geocode")
            return None
        else:
            data = await self._request_with_key(ENDPOINTS["geocode"], params, self.api_key)
            if data is not None:
                results = data.get("results", [])
                if isinstance(results, list) and results:
                    first = results[0]
                    if isinstance(first, dict):
                        return first
            return None

    def is_available(self) -> bool:
        return self.enabled


_client: MapsClient | None = None


def get_maps_client(rotator=None) -> MapsClient:
    """
    Get or create the global Maps client instance.
    
    Args:
        rotator: Optional APIKeyRotator instance for multi-key rotation
    
    Returns:
        Global MapsClient instance
    """
    global _client
    if _client is None:
        _client = MapsClient(rotator=rotator)
    elif rotator and not _client.rotator:
        # Update client with rotator if provided later
        _client.rotator = rotator
        _client.enabled = bool(_client.api_key or (rotator and rotator.available_keys))
    return _client

