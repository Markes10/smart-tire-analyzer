"""
Ollama reasoning service for local Llama driving advice.

Llama3:8b is a text model, so Street View images are summarized by the maps
service first. This service sends the tire predictions plus that route/road
summary to Ollama and asks for structured safety guidance.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
VALID_URGENCY = {"immediate", "within_1000km", "within_5000km", "monitor"}
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", "12"))


class OllamaService:
    """Local Ollama client for route-aware driving recommendations."""

    def __init__(self) -> None:
        configured_base_url = settings.OLLAMA_BASE_URL or os.getenv("OLLAMA_HOST", "")
        base_urls = [
            configured_base_url,
            "http://127.0.0.1:11434",
            "http://host.docker.internal:11434",
        ]
        self.base_urls = list(dict.fromkeys(url.rstrip("/") for url in base_urls if url))
        self.model = settings.OLLAMA_MODEL or "llama3:8b"

    async def reason(self, predictions: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.base_urls:
            return None

        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a tire safety engineer and defensive-driving advisor. "
                        "Use the supplied tire analysis, road context, Street View summary, "
                        "terrain, traffic, and weather to give concise safety advice. "
                        "Respond only with valid JSON."
                    ),
                },
                {"role": "user", "content": self._build_prompt(predictions, context)},
            ],
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }

        last_error = ""
        timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT_SECONDS)
        for base_url in self.base_urls:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{base_url}/api/chat",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    ) as resp:
                        text = await resp.text()
                        if resp.status >= 400:
                            last_error = f"Ollama {resp.status}: {text[:300]}"
                            continue
                        data = json.loads(text) if text else {}

                content = data.get("message", {}).get("content", "").strip()
                parsed = self._extract_json_object(content)
                normalized = self._normalize_reasoning(parsed, predictions)
                if normalized:
                    normalized["source"] = f"ollama:{self.model}"
                    return normalized
            except Exception as exc:
                last_error = str(exc)

        if last_error:
            logger.warning("Ollama reasoning unavailable: %s", last_error)
        return None

    def _build_prompt(self, predictions: Dict[str, Any], context: Dict[str, Any]) -> str:
        tread = predictions.get("tread_depths_mm", {})
        wear = predictions.get("wear_pattern", {})

        return f"""
Analyze this tire and route context for driving safety.

Tire:
- Average tread depth: {tread.get("average", "unknown")} mm
- Minimum tread depth: {tread.get("min", "unknown")} mm
- Health score: {predictions.get("health_score", "unknown")}/10
- Remaining life estimate: {predictions.get("remaining_life_km", "unknown")} km
- Wear pattern: {wear.get("label", "unknown")}
- Wear cause: {wear.get("cause", "unknown")}
- Wear severity: {wear.get("severity", "unknown")}

Route and road:
- Source: {context.get("route_source_latitude", context.get("latitude"))}, {context.get("route_source_longitude", context.get("longitude"))}
- Destination: {context.get("route_destination_latitude", "not provided")}, {context.get("route_destination_longitude", "not provided")}
- Distance: {context.get("route_distance_km", "unknown")} km
- Road condition: {context.get("road_condition", "unknown")}
- Road condition basis: {context.get("road_condition_basis", "unknown")}
- Terrain: {context.get("terrain_type", "unknown")}
- Traffic: {context.get("traffic_density", "unknown")}
- Street View available: {context.get("street_view_available", False)}
- Street View summary: {context.get("street_view_visual_summary", "not available")}

Weather:
- Condition: {context.get("weather_condition", "unknown")}
- Temperature: {context.get("temperature_c", "unknown")} C
- Rain detected: {context.get("rain_detected", False)}
- Visibility: {context.get("visibility_km", "unknown")} km

Return JSON with exactly these fields:
{{
  "risk_level": "CRITICAL|HIGH|MODERATE|LOW",
  "driving_advice": "1-2 direct sentences telling the driver how to drive on this route",
  "replacement_recommended": true,
  "replacement_urgency": "immediate|within_1000km|within_5000km|monitor",
  "primary_cause": "short cause",
  "additional_notes": "optional extra maintenance note",
  "safety_score": 0
}}
""".strip()

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _normalize_reasoning(
        self,
        raw: Optional[Dict[str, Any]],
        predictions: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        risk = str(raw.get("risk_level", "")).upper().strip()
        if risk not in VALID_RISK_LEVELS:
            risk = self._risk_from_predictions(predictions)

        urgency = str(raw.get("replacement_urgency", "monitor")).lower().strip()
        if urgency not in VALID_URGENCY:
            urgency = "monitor"

        safety_score = raw.get("safety_score")
        try:
            safety_score = max(0, min(100, int(safety_score)))
        except (TypeError, ValueError):
            health = float(predictions.get("health_score") or 5.0)
            safety_score = int(max(0, min(100, health * 10)))

        advice = str(raw.get("driving_advice", "")).strip()
        if len(advice) < 10:
            advice = "Drive conservatively, keep extra following distance, and avoid sudden braking until the tire is inspected."

        return {
            "source": "ollama",
            "risk_level": risk,
            "driving_advice": advice,
            "replacement_recommended": bool(raw.get("replacement_recommended", risk in {"CRITICAL", "HIGH"})),
            "replacement_urgency": urgency,
            "primary_cause": str(raw.get("primary_cause", "Tire and route conditions")).strip(),
            "additional_notes": str(raw.get("additional_notes", "")).strip() or None,
            "safety_score": safety_score,
        }

    def _risk_from_predictions(self, predictions: Dict[str, Any]) -> str:
        tread = predictions.get("tread_depths_mm", {})
        avg_tread = float(tread.get("average") or 5.0)
        health = float(predictions.get("health_score") or 5.0)
        if avg_tread < 1.6 or health < 2.0:
            return "CRITICAL"
        if avg_tread < 3.0 or health < 4.0:
            return "HIGH"
        if avg_tread < 5.0 or health < 6.0:
            return "MODERATE"
        return "LOW"
