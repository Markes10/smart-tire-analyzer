"""
Weather Client — OpenWeatherMap API low-level HTTP client with rotation support.
"""

import os
import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
DEFAULT_TIMEOUT = 5  # seconds


class WeatherClient:
    """
    Low-level OpenWeatherMap API client with rotation support.
    Fetches real-time weather and 5-day forecast data.
    """

    def __init__(self, api_key: Optional[str] = None, rotator=None):
        """
        Initialize Weather client.
        
        Args:
            api_key: Single API key (for backward compatibility)
            rotator: APIKeyRotator instance for multi-key rotation
        """
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        self.rotator = rotator
        self.enabled = bool(self.api_key or (rotator and rotator.available_keys))
        if not self.enabled:
            logger.warning("OPENWEATHER_API_KEY not configured and no rotator provided")

    async def _get_weather_single_key(
        self,
        url: str,
        lat: float,
        lon: float,
        api_key: str,
        hours: int = None,
    ) -> Optional[Dict]:
        """Make a single weather API request with given key."""
        params = {
            "lat": lat, "lon": lon,
            "appid": api_key,
            "units": "metric",
        }
        if hours is not None:
            params["cnt"] = hours // 3  # 3-hour intervals

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            ) as session:
                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                logger.error("OpenWeatherMap: Invalid API key")
            elif e.status == 429:
                logger.warning("OpenWeatherMap: Rate limit exceeded (429)")
            else:
                logger.warning(f"OpenWeatherMap HTTP {e.status}: {e.message}")
        except aiohttp.ClientConnectorError:
            logger.warning("OpenWeatherMap: Connection failed (no internet?)")
        except Exception as e:
            logger.warning(f"OpenWeatherMap error: {e}")
        return None

    async def get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Fetch current weather for a coordinate.
        Automatically rotates to next API key on failure or quota exceeded.

        Returns:
            Raw OpenWeatherMap API response dict, or None on failure
        """
        if not self.enabled:
            return None

        # Try with rotation if available, otherwise use single key
        if self.rotator:
            available_keys = self.rotator.available_quota_keys
            if not available_keys:
                logger.error("No Weather API keys with available quota")
                return None

            # Try each available key
            for attempt, key in enumerate(available_keys):
                result = await self._get_weather_single_key(WEATHER_URL, lat, lon, key)
                if result is not None:
                    self.rotator.record_successful_request(key)
                    return result
                else:
                    self.rotator.record_error(key, "Weather request failed")
                    if attempt < len(available_keys) - 1:
                        logger.warning(f"Retrying with next Weather API key...")
                        self.rotator.rotate_to_next_key()
            
            logger.error("All available Weather API keys failed")
            return None
        else:
            return await self._get_weather_single_key(WEATHER_URL, lat, lon, self.api_key)

    async def get_forecast(self, lat: float, lon: float, hours: int = 24) -> Optional[list]:
        """
        Fetch weather forecast for next N hours.
        Automatically rotates to next API key on failure or quota exceeded.
        
        Returns list of forecast periods, or None on failure.
        """
        if not self.enabled:
            return None

        # Try with rotation if available
        if self.rotator:
            available_keys = self.rotator.available_quota_keys
            if not available_keys:
                logger.error("No Weather API keys with available quota")
                return None

            # Try each available key
            for attempt, key in enumerate(available_keys):
                try:
                    result = await self._get_weather_single_key(FORECAST_URL, lat, lon, key, hours)
                    if result is not None:
                        data = await self._parse_forecast(result)
                        if data is not None:
                            self.rotator.record_successful_request(key)
                            return data
                    else:
                        self.rotator.record_error(key, "Forecast request failed")
                except Exception as e:
                    logger.warning(f"Forecast error with key: {e}")
                    self.rotator.record_error(key, str(e))

                if attempt < len(available_keys) - 1:
                    logger.warning(f"Retrying forecast with next Weather API key...")
                    self.rotator.rotate_to_next_key()
            
            logger.error("All available Weather API keys failed for forecast")
            return None
        else:
            result = await self._get_weather_single_key(FORECAST_URL, lat, lon, self.api_key, hours)
            if result is not None:
                return await self._parse_forecast(result)
            return None

    async def _parse_forecast(self, data: Dict) -> Optional[list]:
        """Parse forecast response."""
        try:
            return data.get("list", [])
        except Exception as e:
            logger.warning(f"Forecast parse error: {e}")
            return None

    def is_available(self) -> bool:
        return self.enabled


# Singleton
_client: Optional[WeatherClient] = None

def get_weather_client(rotator=None) -> WeatherClient:
    """
    Get or create the global Weather client instance.
    
    Args:
        rotator: Optional APIKeyRotator instance for multi-key rotation
    
    Returns:
        Global WeatherClient instance
    """
    global _client
    if _client is None:
        _client = WeatherClient(rotator=rotator)
    elif rotator and not _client.rotator:
        # Update client with rotator if provided later
        _client.rotator = rotator
        _client.enabled = bool(_client.api_key or (rotator and rotator.available_keys))
    return _client

