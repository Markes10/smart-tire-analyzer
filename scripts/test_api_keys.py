"""
Simple async script to test external API keys for Maps, Weather, and Gemini.
Usage:
  - Copy `.env.example` to `.env` and fill your keys, or set env variables.
  - Activate the Python venv, then run:
      python scripts/test_api_keys.py

This script will initialize rotators using `app.config.settings` and make
one small request per service. It prints results and returns non-zero on
failure.
"""

import asyncio
import os
import sys
import logging

from app.config import settings
from app.services.api_key_rotator import initialize_rotators, get_gemini_rotator, get_weather_rotator, get_maps_rotator
from api_integrations.google_maps.maps_client import get_maps_client
from api_integrations.weather.weather_client import get_weather_client
from api_integrations.gemini.gemini_client import get_gemini_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_api_keys")


async def main():
    # Initialize rotators from settings (reads .env at project root)
    initialize_rotators(
        gemini_keys=settings.get_gemini_keys(),
        weather_keys=settings.get_weather_keys(),
        maps_keys=settings.get_maps_keys(),
        mapillary_keys=settings.get_mapillary_keys(),
    )

    gm_rot = get_gemini_rotator()
    we_rot = get_weather_rotator()
    mp_rot = get_maps_rotator()

    maps_client = get_maps_client(rotator=mp_rot)
    weather_client = get_weather_client(rotator=we_rot)
    gemini_client = get_gemini_client(rotator=gm_rot)

    # Sample coordinate (San Francisco)
    lat, lon = 37.7749, -122.4194

    ok = True

    # Test Maps elevation
    try:
        logger.info("Testing Maps elevation for %s,%s", lat, lon)
        elev = await maps_client.get_elevation(lat, lon)
        logger.info("Maps elevation result: %s", elev)
        if elev is None:
            ok = False
    except Exception as e:
        logger.exception("Maps test failed: %s", e)
        ok = False

    # Test Weather
    try:
        logger.info("Testing Weather for %s,%s", lat, lon)
        w = await weather_client.get_current_weather(lat, lon)
        logger.info("Weather result summary: %s", (w and w.get("weather", [{}])[0].get("main")))
        if w is None:
            ok = False
    except Exception as e:
        logger.exception("Weather test failed: %s", e)
        ok = False

    # Test Gemini (text prompt) — conservative token limit
    try:
        logger.info("Testing Gemini generate with minimal prompt")
        if gemini_client.is_available():
            text = await gemini_client.generate("Return a one-word JSON: {\"ok\":true}", max_tokens=50)
            logger.info("Gemini response (truncated): %s", (text[:300] if text else None))
            if text is None:
                ok = False
        else:
            logger.warning("Gemini client reports not enabled — no keys configured")
            ok = False
    except Exception as e:
        logger.exception("Gemini test failed: %s", e)
        ok = False

    if not ok:
        logger.error("One or more external API checks failed or returned no data.")
        sys.exit(2)

    logger.info("All external API checks returned data (success).")


if __name__ == "__main__":
    asyncio.run(main())
