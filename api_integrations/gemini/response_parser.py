"""
Response Parser — Extracts and validates structured data from Gemini API responses.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
VALID_URGENCY = {"immediate", "within_1000km", "within_5000km", "monitor"}


def parse_reasoning_response(raw: Optional[Dict]) -> Optional[Dict]:
    """
    Validate and normalize a Gemini reasoning response dict.

    Args:
        raw: Raw parsed JSON dict from Gemini

    Returns:
        Normalized dict with validated fields, or None if invalid
    """
    if not raw or not isinstance(raw, dict):
        return None

    # Normalize risk level
    risk = str(raw.get("risk_level", "MODERATE")).upper().strip()
    if risk not in VALID_RISK_LEVELS:
        logger.warning(f"Invalid risk_level from Gemini: {risk!r} — defaulting to MODERATE")
        risk = "MODERATE"

    # Normalize urgency
    urgency = str(raw.get("replacement_urgency", "monitor")).lower().strip()
    if urgency not in VALID_URGENCY:
        urgency = "monitor"

    # Safety score clamping
    safety_score = raw.get("safety_score")
    if safety_score is not None:
        try:
            safety_score = max(0, min(100, int(safety_score)))
        except (ValueError, TypeError):
            safety_score = None

    # Validate driving advice
    advice = str(raw.get("driving_advice", "")).strip()
    if not advice or len(advice) < 10:
        advice = "Inspect tire condition and consult a professional if unsure."

    return {
        "source": "gemini",
        "risk_level": risk,
        "driving_advice": advice,
        "replacement_recommended": bool(raw.get("replacement_recommended", False)),
        "replacement_urgency": urgency,
        "primary_cause": str(raw.get("primary_cause", "Unknown")).strip(),
        "additional_notes": str(raw.get("additional_notes", "")).strip() or None,
        "safety_score": safety_score,
    }


def extract_risk_level(text: str) -> str:
    """
    Extract risk level from free-text Gemini response (fallback parsing).
    Used when JSON parsing fails.
    """
    text_upper = text.upper()
    if "CRITICAL" in text_upper:
        return "CRITICAL"
    if "HIGH" in text_upper:
        return "HIGH"
    if "MODERATE" in text_upper:
        return "MODERATE"
    return "LOW"


def extract_replacement_flag(text: str) -> bool:
    """Extract replacement recommendation from free text."""
    t = text.lower()
    replace_keywords = ["replace", "replacement", "new tire", "immediate"]
    no_replace_keywords = ["no replacement", "not necessary", "monitor only"]
    if any(kw in t for kw in no_replace_keywords):
        return False
    return any(kw in t for kw in replace_keywords)
