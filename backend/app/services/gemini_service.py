"""
Gemini AI Reasoning Service
Uses Google Gemini API to generate intelligent tire analysis reasoning,
driving advice, and replacement recommendations.
Falls back to rule-based system when API is unavailable.
"""

import hashlib
import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any

from app.config import settings
from app.services.api_key_rotator import get_gemini_rotator, APIKeyRotator
from app.services.cache_service import get_cache

logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{settings.GEMINI_MODEL}:generateContent"
)
GEMINI_TIMEOUT = 10  # seconds


REASONING_PROMPT_TEMPLATE = """
You are an expert tire safety engineer and automotive advisor.
Analyze the following tire condition data and provide a safety assessment.

## Tire Analysis Data:
- Average Tread Depth: {avg_tread_mm:.1f} mm (Legal minimum: 1.6mm, Replace threshold: 3.0mm)
- Tread Readings: T1={t1:.1f}mm, T2={t2:.1f}mm, T3={t3:.1f}mm, T4={t4:.1f}mm
- Tire Health Score: {health_score:.1f}/10
- Estimated Remaining Life: {remaining_km:.0f} km
- Wear Pattern: {wear_pattern} (Cause: {wear_cause})
- Wear Pattern Severity: {wear_severity}

## Environmental Context:
- Location: {location}
- Road Condition: {road_condition}
- Terrain Type: {terrain_type}
- Traffic Density: {traffic_density}
- Weather: {weather}
- Temperature: {temperature}
- Humidity: {humidity}
- Visibility: {visibility}
- Rain: {rain_detected}

## Required Output (respond ONLY with valid JSON):
{{
  "risk_level": "<CRITICAL|HIGH|MODERATE|LOW>",
  "driving_advice": "<1-2 sentences of specific, actionable driving advice>",
  "replacement_recommended": <true|false>,
  "replacement_urgency": "<immediate|within_1000km|within_5000km|monitor>",
  "primary_cause": "<main cause of tire condition>",
  "additional_notes": "<optional: inflation pressure advice, alignment check, etc.>",
  "safety_score": <0-100 integer>
}}

Be concise, specific, and safety-first in your assessment.
"""


class GeminiService:
    """
    Google Gemini API client for AI-powered tire reasoning.
    
    Features:
    - Async API calls with timeout
    - Automatic retry on transient failures  
    - Rule-based fallback when API unavailable
    - Prompt caching for duplicate requests
    - Supports runtime API keys passed from frontend users
    """

    def __init__(self, runtime_keys: dict | None = None):
        """
        Initialize the Gemini service.
        
        Args:
            runtime_keys: Optional dict with a "gemini" key for user-provided API key.
                          If provided, this takes priority over env-var keys.
        """
        runtime_gemini_key = None
        if runtime_keys and isinstance(runtime_keys, dict):
            runtime_gemini_key = runtime_keys.get("gemini") or runtime_keys.get("GEMINI_API_KEY") or None

        if runtime_gemini_key:
            # Use the user-provided key directly
            logger.info("GeminiService initialized with runtime API key")
            self.rotator = APIKeyRotator("gemini", [runtime_gemini_key], daily_quota=9999)
            self.enabled = True
        else:
            # Prefer the global, quota-aware rotator initialized in main.py
            rot = get_gemini_rotator()
            if not rot:
                # Fallback: create a local rotator from settings if available
                keys = settings.get_gemini_keys()
                rot = APIKeyRotator("gemini", keys, daily_quota=settings.GEMINI_DAILY_QUOTA) if keys else None

            self.rotator = rot
            self.enabled = bool(self.rotator and self.rotator.available_keys)
            if not self.enabled:
                logger.warning("No Gemini API keys configured — will use rule-based reasoning fallback")

    async def reason(
        self,
        predictions: Dict,
        context: Dict,
        max_retries: int = 2,
    ) -> Dict:
        """
        Generate AI reasoning from tire predictions + environmental context.

        Args:
            predictions: Model output dict (tread_depths_mm, health_score, etc.)
            context: Weather + Maps context dict
            max_retries: Number of API retry attempts

        Returns:
            Reasoning dict with risk_level, advice, replacement recommendation
        """
        if not self.enabled:
            return self._rule_based_fallback(predictions)

        prompt = self._build_prompt(predictions, context)

        # Try cache before making API call
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        cache = get_cache()
        cache_key = f"gemini:{prompt_hash}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for Gemini reasoning")
            return cached

        # Try each configured key once (rotate on quota/forbidden/timeouts)
        if not self.enabled:
            return self._rule_based_fallback(predictions)

        attempts = 0
        max_attempts = max(1, len(self.rotator.available_keys))
        while attempts < max_attempts:
            key = self.rotator.get_current_key()
            try:
                result = await self._call_gemini(prompt, api_key=key)
                # Record usage and return
                try:
                    self.rotator.record_successful_request(key)
                except Exception:
                    pass
                result["source"] = "gemini"
                await cache.set(cache_key, result, ttl=86400)
                return result
            except aiohttp.ClientResponseError as e:
                status = getattr(e, "status", None)
                message = getattr(e, "message", "request failed")
                logger.warning("Gemini HTTP error (status=%s): %s", status, message)
                # Rotate keys on quota/forbidden/unauthorized
                if status in (429, 403, 401):
                    logger.info("Rotating Gemini API key due to HTTP status %s", status)
                    try:
                        self.rotator.record_error(key, f"HTTP {status}: {message}")
                        self.rotator.rotate_to_next_key()
                    except Exception:
                        pass
                    attempts += 1
                    continue
                break
            except asyncio.TimeoutError:
                logger.warning("Gemini timeout — rotating key and retrying")
                try:
                    self.rotator.record_error(key, "timeout")
                    self.rotator.rotate_to_next_key()
                except Exception:
                    pass
                attempts += 1
                continue
            except Exception as e:
                logger.warning(f"Gemini error: {e}")
                break

        logger.warning("All Gemini attempts failed — using rule-based fallback")
        return self._rule_based_fallback(predictions)

    def _build_prompt(self, predictions: Dict, context: Dict) -> str:
        """Build the Gemini reasoning prompt from prediction + context data."""
        tread = predictions.get("tread_depths_mm", {})
        wear = predictions.get("wear_pattern", {})

        try:
            from api_integrations.gemini import prompt_builder

            prompt = prompt_builder.build_tire_reasoning_prompt(
                predictions,
                context,
                include_examples=True,
            )
            confidence = float(predictions.get("confidence", wear.get("confidence", 1.0)))
            if confidence < 0.65:
                metadata = predictions.get("metadata") if isinstance(predictions.get("metadata"), dict) else {}
                anomaly_features = {
                    "wear_pattern": wear.get("label", "unknown"),
                    "tread_depths_mm": tread,
                    "condition_prediction": predictions.get("condition_prediction"),
                    "model_diagnostics": metadata.get("model_diagnostics", {}),
                }
                prompt = (
                    prompt
                    + "\n\n"
                    + prompt_builder.build_anomaly_detection_prompt(anomaly_features, confidence)
                )
            return prompt
        except Exception as exc:
            logger.debug("Gemini prompt_builder unavailable; using legacy template: %s", exc)

        return REASONING_PROMPT_TEMPLATE.format(
            avg_tread_mm=tread.get("average", 0.0),
            t1=tread.get("tread_1", 0.0),
            t2=tread.get("tread_2", 0.0),
            t3=tread.get("tread_3", 0.0),
            t4=tread.get("tread_4", 0.0),
            health_score=predictions.get("health_score", 0.0),
            remaining_km=predictions.get("remaining_life_km", 0.0),
            wear_pattern=wear.get("label", "unknown"),
            wear_cause=wear.get("cause", "unknown"),
            wear_severity=wear.get("severity", "unknown"),
            location=f"{context.get('latitude', 'N/A')}, {context.get('longitude', 'N/A')}",
            road_condition=context.get("road_condition", "unknown"),
            terrain_type=context.get("terrain_type", "unknown"),
            traffic_density=context.get("traffic_density", "unknown"),
            weather=context.get("weather_condition", "unknown"),
            temperature=f"{context.get('temperature_c', 'N/A')}°C",
            humidity=f"{context.get('humidity_pct', 'N/A')}%",
            visibility=f"{context.get('visibility_km', 'N/A')} km",
            rain_detected=str(context.get("rain_detected", False)),
        )

    async def _call_gemini(self, prompt: str, api_key: Optional[str]) -> Dict[str, Any]:
        """Make async HTTP call to Gemini API and parse JSON response."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "risk_level": {"type": "string", "enum": ["CRITICAL", "HIGH", "MODERATE", "LOW"]},
                        "driving_advice": {"type": "string"},
                        "replacement_recommended": {"type": "boolean"},
                        "replacement_urgency": {
                            "type": "string",
                            "enum": ["immediate", "within_1000km", "within_5000km", "monitor"],
                        },
                        "primary_cause": {"type": "string"},
                        "additional_notes": {"type": "string"},
                        "safety_score": {"type": "integer"},
                    },
                    "required": [
                        "risk_level",
                        "driving_advice",
                        "replacement_recommended",
                        "replacement_urgency",
                        "primary_cause",
                        "safety_score",
                    ],
                },
            },
        }
        if not api_key:
            raise RuntimeError("No Gemini API key available")
        url = f"{GEMINI_API_URL}?key={api_key}"

        timeout = aiohttp.ClientTimeout(total=GEMINI_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()

        # Extract text from Gemini response
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        # Parse JSON response and ensure we return a dict (avoid Any return)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Gemini returned JSON that is not an object/dict")
        except json.JSONDecodeError:
            # Try to extract JSON object from response text
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse Gemini response as JSON: {text[:200]}")

    def _rule_based_fallback(self, predictions: Dict) -> Dict:
        """
        Rule-based reasoning when Gemini API is unavailable.
        Implements deterministic safety logic based on tread depth thresholds.
        """
        tread = predictions.get("tread_depths_mm", {})
        avg_tread = tread.get("average", 5.0)
        health = predictions.get("health_score", 5.0)
        wear_info = predictions.get("wear_pattern", {})
        wear_label = wear_info.get("label", "uniform_wear")
        wear_severity = wear_info.get("severity", "low")

        # Determine risk level
        if avg_tread < 1.6 or health < 2.0 or wear_severity == "critical":
            risk = "CRITICAL"
            advice = "Stop driving immediately. Tires are unsafe and must be replaced before next use."
            urgency = "immediate"
            replace = True
        elif avg_tread < 3.0 or health < 4.0:
            risk = "HIGH"
            advice = "Schedule tire replacement within 1,000 km. Reduce speed in wet conditions."
            urgency = "within_1000km"
            replace = True
        elif avg_tread < 5.0 or health < 6.0:
            risk = "MODERATE"
            advice = "Monitor tire condition closely. Plan replacement within 5,000 km."
            urgency = "within_5000km"
            replace = False
        else:
            risk = "LOW"
            advice = "Tires in acceptable condition. Maintain recommended pressure and inspect monthly."
            urgency = "monitor"
            replace = False

        # Add wear-specific advice
        wear_notes = {
            "center_wear": "Check and reduce tire inflation pressure.",
            "edge_wear": "Check and increase tire inflation pressure.",
            "side_wall_wear": "Inspect wheel alignment, camber, and the outer shoulder before continued use.",
            "patchy_wear": "Have wheel alignment and balance checked.",
            "one_side_wear": "Inspect camber angle — alignment adjustment required.",
            "cupping_wear": "Inspect shock absorbers and suspension immediately.",
            "uniform_wear": None,
        }
        additional = wear_notes.get(wear_label)

        return {
            "source": "rule_based",
            "risk_level": risk,
            "driving_advice": advice,
            "replacement_recommended": replace,
            "replacement_urgency": urgency,
            "primary_cause": wear_info.get("cause", "General wear"),
            "additional_notes": additional,
            "safety_score": int(max(0, min(100, health * 10))),
        }
