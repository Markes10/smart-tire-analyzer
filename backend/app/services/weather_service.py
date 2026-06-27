"""
Weather Service — OpenWeatherMap API integration.
Fetches temperature, rain, humidity, visibility for risk context.
Falls back to safe defaults when API key not configured.
"""

import os
import logging
import aiohttp
from typing import Dict

from app.config import settings
from app.services.api_key_rotator import get_weather_rotator, APIKeyRotator
from app.services.cache_service import get_cache

logger = logging.getLogger(__name__)
OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"


class WeatherService:
    def __init__(self, runtime_keys: dict | None = None):
        """
        Initialize the Weather service.
        
        Args:
            runtime_keys: Optional dict with "openweather" key for user-provided API key.
        """
        runtime_weather_key = None
        if runtime_keys and isinstance(runtime_keys, dict):
            runtime_weather_key = runtime_keys.get("openweather") or runtime_keys.get("OPENWEATHER_API_KEY") or None

        if runtime_weather_key:
            logger.info("WeatherService initialized with runtime API key")
            self.rotator = APIKeyRotator("weather", [runtime_weather_key], daily_quota=9999)
            self.enabled = True
        else:
            rot = get_weather_rotator()
            if not rot:
                keys = settings.get_weather_keys()
                rot = APIKeyRotator("weather", keys, daily_quota=settings.OPENWEATHER_DAILY_QUOTA) if keys else None

            self.rotator = rot
            self.enabled = bool(self.rotator and self.rotator.available_keys)
            if not self.enabled:
                logger.warning("No Weather API keys configured — using mock weather data")

    async def get_weather(self, lat: float, lon: float) -> Dict:
        """
        Fetch: temperature (°C), humidity (%), visibility (km),
               rain status, condition string, and weather_risk_multiplier.
        """
        if not self.enabled:
            return self._mock_weather()

        cache = get_cache()
        cache_key = f"weather:{round(lat, 4)}:{round(lon, 4)}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        attempts = 0
        max_attempts = max(1, len(self.rotator.available_keys))
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while attempts < max_attempts:
                key = self.rotator.get_current_key()
                params = {"lat": lat, "lon": lon, "appid": key, "units": "metric"}
                try:
                    async with session.get(OWM_BASE, params=params) as resp:
                        resp.raise_for_status()
                        data = await resp.json()

                    condition = data["weather"][0]["main"] if data.get("weather") else "Clear"
                    temp_c = data["main"]["temp"]
                    humidity_pct = data["main"]["humidity"]
                    visibility_km = data.get("visibility", 10000) / 1000.0
                    rain_detected = "rain" in data or "drizzle" in data.get("weather", [{}])[0].get("main", "").lower()

                    try:
                        self.rotator.record_successful_request(key)
                    except Exception:
                        pass

                    result = {
                        "weather_condition": condition,
                        "temperature_c": round(temp_c, 1),
                        "humidity_pct": humidity_pct,
                        "visibility_km": round(visibility_km, 1),
                        "rain_detected": rain_detected,
                        "weather_risk_multiplier": self._weather_risk_mult(condition, rain_detected, temp_c),
                    }
                    await cache.set(cache_key, result, ttl=1800)
                    return result
                except aiohttp.ClientResponseError as e:
                    status = getattr(e, "status", None)
                    message = getattr(e, "message", "request failed")
                    logger.warning("Weather API HTTP error (status=%s): %s", status, message)
                    if status in (429, 403, 401):
                        logger.info("Rotating Weather API key due to HTTP status %s", status)
                        try:
                            self.rotator.record_error(key, f"HTTP {status}: {message}")
                            self.rotator.rotate_to_next_key()
                        except Exception:
                            pass
                        attempts += 1
                        continue
                    logger.warning("Weather API unrecoverable HTTP error: %s", e)
                    break
                except Exception as e:
                    logger.warning(f"Weather API error: {e} — trying next key")
                    try:
                        self.rotator.record_error(key, str(e))
                        self.rotator.rotate_to_next_key()
                    except Exception:
                        pass
                    attempts += 1
                    continue

        return self._mock_weather()

    def _weather_risk_mult(self, condition: str, rain: bool, temp_c: float) -> float:
        """
        Multiplier applied to remaining tire life based on conditions.
        Rain and extreme temps degrade tires faster → higher multiplier.
        """
        mult = 1.0
        if rain or condition.lower() in ("rain", "drizzle", "thunderstorm"):
            mult *= 1.15
        if condition.lower() in ("snow", "sleet", "blizzard"):
            mult *= 1.30
        if temp_c > 40:
            mult *= 1.08   # Extreme heat accelerates rubber wear
        if temp_c < -10:
            mult *= 1.05   # Extreme cold stiffens rubber
        return round(mult, 3)

    def _mock_weather(self) -> Dict:
        return {
            "weather_condition": "Clear",
            "temperature_c": 24.0,
            "humidity_pct": 55,
            "visibility_km": 10.0,
            "rain_detected": False,
            "weather_risk_multiplier": 1.0,
        }
