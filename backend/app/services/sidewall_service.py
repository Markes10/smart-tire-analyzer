"""
Sidewall Service — Backend service that orchestrates Gemini Vision sidewall
extraction and enriches the analysis report with tire metadata.

Flow:
  1. Receive sidewall image bytes from the API route
  2. Dispatch to SidewallAnalyzer (Gemini Vision)
  3. Merge extracted brand / size / DOT info into the analysis result
  4. Override any user-provided brand/size hints if Gemini has higher confidence

This service is intentionally non-blocking (async) and never raises —
any failure returns a gracefully degraded empty result so that the main
tread-depth analysis is unaffected.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SidewallService:
    """
    Service layer for Gemini-powered sidewall text extraction.

    Designed to be injected into the inference route alongside
    InferenceService, GeminiService, etc.
    """

    # ── public API ────────────────────────────────────────────────────────────

    async def extract_tire_details(
        self,
        sidewall_image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> Dict:
        """
        Extract tire metadata from a sidewall image via Gemini Vision.

        Args:
            sidewall_image_bytes: Raw bytes of the sidewall photo.
            mime_type:            MIME type of the image.

        Returns:
            Structured dict of tire details (always returned, never raises).
            Key fields:
              brand, tire_model, tire_size, load_index, speed_rating,
              dot_code, manufacture_week, manufacture_year,
              construction_type, max_pressure_psi, special_markings,
              extraction_confidence, source
        """
        try:
            from api_integrations.gemini.sidewall_analyzer import get_sidewall_analyzer
            analyzer = get_sidewall_analyzer()
            result = await analyzer.extract(sidewall_image_bytes, mime_type=mime_type)
            logger.info(
                "Sidewall extraction: brand=%s size=%s confidence=%s",
                result.get("brand"),
                result.get("tire_size", {}).get("full_formatted"),
                result.get("extraction_confidence"),
            )
            return result
        except Exception as e:
            logger.error("SidewallService.extract_tire_details failed: %s", e)
            return {"source": "error", "extraction_notes": str(e)}

    def merge_into_report(
        self,
        report: Dict,
        sidewall_details: Dict,
        user_hints: Optional[Dict] = None,
    ) -> Dict:
        """
        Merge extracted sidewall metadata into the main analysis report.

        Priority:
          Gemini HIGH confidence  >  Gemini MEDIUM confidence  >  user-provided hints

        Args:
            report:           The main analysis report dict (modified in-place + returned).
            sidewall_details: Output from extract_tire_details().
            user_hints:       Dict of user-supplied brand/tire_model/tire_size.

        Returns:
            The enriched report dict.
        """
        user_hints = user_hints or {}
        confidence = sidewall_details.get("extraction_confidence", "LOW")
        source = sidewall_details.get("source", "unavailable")

        # Attach full sidewall block to report
        report["sidewall_analysis"] = sidewall_details

        # Skip merge if extraction was not successful
        if source not in ("gemini_vision",):
            logger.info("Sidewall merge skipped — source=%s", source)
            return report

        # Brand
        if sidewall_details.get("brand") and confidence in ("HIGH", "MEDIUM"):
            report["tire_brand"] = sidewall_details["brand"]
        elif user_hints.get("tire_brand"):
            report.setdefault("tire_brand", user_hints["tire_brand"])

        # Tire model
        if sidewall_details.get("tire_model") and confidence == "HIGH":
            report["tire_model"] = sidewall_details["tire_model"]
        elif user_hints.get("tire_model"):
            report.setdefault("tire_model", user_hints["tire_model"])

        # Tire size
        size_info = sidewall_details.get("tire_size", {})
        formatted_size = size_info.get("full_formatted")
        if formatted_size and confidence in ("HIGH", "MEDIUM"):
            report["tire_size"] = formatted_size
        elif user_hints.get("tire_size"):
            report.setdefault("tire_size", user_hints["tire_size"])

        # Speed Rating & Load Index
        if sidewall_details.get("speed_rating"):
            report["speed_rating"] = sidewall_details["speed_rating"]
        if sidewall_details.get("load_index"):
            report["load_index"] = sidewall_details["load_index"]

        # Manufacture date from DOT code
        dot = sidewall_details.get("dot_code", {})
        if dot.get("manufacture_year"):
            report["manufacture_year"] = dot["manufacture_year"]
        if dot.get("manufacture_week"):
            report["manufacture_week"] = dot["manufacture_week"]
        if dot.get("manufacture_date_text"):
            report["manufacture_date"] = dot["manufacture_date_text"]

        # Construction type
        if sidewall_details.get("construction_type"):
            report["construction_type"] = sidewall_details["construction_type"]

        # Max pressure
        if sidewall_details.get("max_pressure_psi"):
            report["max_pressure_psi"] = sidewall_details["max_pressure_psi"]

        # Special markings
        markings = sidewall_details.get("special_markings", [])
        if markings:
            report["special_markings"] = markings

        # Country of origin
        if sidewall_details.get("country_of_origin"):
            report["country_of_origin"] = sidewall_details["country_of_origin"]

        logger.info(
            "Report enriched with sidewall data — brand=%s size=%s year=%s",
            report.get("tire_brand"),
            report.get("tire_size"),
            report.get("manufacture_year"),
        )
        return report
