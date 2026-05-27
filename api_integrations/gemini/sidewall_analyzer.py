"""
Sidewall Analyzer — Gemini Vision-powered tire sidewall text extraction.

Replaces traditional OCR (Tesseract / EasyOCR) with Gemini multimodal inference.
Gemini reads the embossed markings from the sidewall photo and returns structured
tire metadata:

  - Brand name        (e.g. "Michelin", "Bridgestone", "Apollo")
  - Tire size         (e.g. "185/65 R15")
  - Load index        (e.g. 88)
  - Speed rating      (e.g. "H")
  - Manufacture date  (DOT week + year, e.g. week=15, year=2022)
  - Construction type (Radial / Bias)
  - Max pressure      (PSI)
  - Country of origin
  - DOT code          (full string)
  - Other markings    (M+S, run-flat, EV, etc.)

All fields are optional / nullable — Gemini returns null when a marking is not
visible or legible in the image.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Extraction prompt ──────────────────────────────────────────────────────────

SIDEWALL_EXTRACTION_PROMPT = """You are an expert automotive tire analyst with 20+ years of experience
reading tire sidewall markings. Your task is to carefully examine the provided tire sidewall
image and extract all visible text and markings with maximum accuracy.

Tire sidewalls contain embossed (raised) text that encodes critical safety and specification data.
Look carefully for:

1. **Brand name** — e.g. MICHELIN, BRIDGESTONE, APOLLO, GOODYEAR, CEAT, MRF, etc.
2. **Tire size** — ISO metric format "WIDTH/ASPECT_RATIO R DIAMETER" e.g. "185/65 R15", "205/55R17"
3. **Load index** — 2-3 digit number after size, e.g. 88, 91, 94
4. **Speed rating** — single letter after load index, e.g. H, V, W, Y, T
5. **DOT code** — begins with "DOT", followed by plant code, tire size code, and 4-digit week/year
   e.g. "DOT MA L9 ABCD 1522" → week=15, year=2022
6. **Construction type** — "R" in size = Radial, "B" = Bias-belted, "D" = Diagonal
7. **Max inflation pressure** — "MAX PRESS XXX kPa" or "XXX PSI"
8. **Country of origin** — "MADE IN ___" text
9. **Special markings** — M+S (mud + snow), OWL (outline white letter), RFT (run-flat),
   EV (electric vehicle optimized), ELECT, etc.
10. **Tire model name** — the specific product line name if legible

Return ONLY valid JSON in this exact schema (use null for any field not visible/legible):
{
  "brand": "<string | null>",
  "tire_model": "<string | null>",
  "tire_size": {
    "raw": "<string | null>",
    "width_mm": <integer | null>,
    "aspect_ratio": <integer | null>,
    "rim_diameter_inches": <integer | null>,
    "full_formatted": "<e.g. '185/65 R15' | null>"
  },
  "load_index": <integer | null>,
  "speed_rating": "<string | null>",
  "dot_code": {
    "full": "<string | null>",
    "manufacture_week": <integer | null>,
    "manufacture_year": <integer | null>,
    "manufacture_date_text": "<e.g. 'Week 15, 2022' | null>"
  },
  "construction_type": "<'Radial' | 'Bias' | null>",
  "max_pressure_psi": <integer | null>,
  "max_pressure_kpa": <integer | null>,
  "country_of_origin": "<string | null>",
  "special_markings": ["<list of strings>"],
  "all_visible_text": "<raw concatenated text you can see on the sidewall>",
  "extraction_confidence": "<'HIGH' | 'MEDIUM' | 'LOW'>",
  "extraction_notes": "<any issues, partial visibility, unclear text, etc.>"
}"""


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _normalise_brand(raw: Optional[str]) -> Optional[str]:
    """Capitalise and correct common brand name variations."""
    if not raw:
        return None
    corrections: Dict[str, str] = {
        "michelin": "Michelin",
        "michelen": "Michelin",
        "bridgeston": "Bridgestone",
        "bridgstone": "Bridgestone",
        "goodyear": "Goodyear",
        "good year": "Goodyear",
        "continetal": "Continental",
        "continental": "Continental",
        "pireli": "Pirelli",
        "pirelly": "Pirelli",
        "yokohamma": "Yokohama",
        "yokohama": "Yokohama",
        "dunlop": "Dunlop",
        "apollo": "Apollo",
        "ceat": "CEAT",
        "mrf": "MRF",
        "jk tyre": "JK Tyre",
        "jktyre": "JK Tyre",
    }
    key = raw.strip().lower()
    return corrections.get(key, raw.strip().title())


def _parse_tire_size(size_str: Optional[str]) -> Dict:
    """Parse a raw tire size string into its numeric components."""
    import re
    empty: Dict = {
        "raw": size_str,
        "width_mm": None,
        "aspect_ratio": None,
        "rim_diameter_inches": None,
        "full_formatted": None,
    }
    if not size_str:
        return empty
    m = re.match(r"(\d{3})\s*/\s*(\d{2})\s*[Rr]\s*(\d{2})", size_str.strip())
    if not m:
        return {**empty, "full_formatted": size_str.strip().upper()}
    w, a, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return {
        "raw": size_str,
        "width_mm": w,
        "aspect_ratio": a,
        "rim_diameter_inches": d,
        "full_formatted": f"{w}/{a} R{d}",
    }


def _normalise_result(raw: Dict) -> Dict:
    """
    Post-process Gemini's raw extraction dict:
    - Correct brand spelling
    - Re-parse tire size for consistency
    - Clamp confidence field
    """
    brand_raw = raw.get("brand")
    raw["brand"] = _normalise_brand(brand_raw)

    # Re-parse tire_size if Gemini returned a string instead of a nested dict
    ts = raw.get("tire_size")
    if isinstance(ts, str):
        raw["tire_size"] = _parse_tire_size(ts)
    elif isinstance(ts, dict):
        # Make sure full_formatted is always present
        if not ts.get("full_formatted") and ts.get("raw"):
            parsed = _parse_tire_size(ts["raw"])
            ts.update(parsed)
    else:
        raw["tire_size"] = _parse_tire_size(None)

    # Ensure special_markings is always a list
    if not isinstance(raw.get("special_markings"), list):
        raw["special_markings"] = []

    # Normalise extraction_confidence
    conf = str(raw.get("extraction_confidence", "LOW")).upper()
    if conf not in {"HIGH", "MEDIUM", "LOW"}:
        conf = "LOW"
    raw["extraction_confidence"] = conf

    return raw


# ── Main analyser class ────────────────────────────────────────────────────────

class SidewallAnalyzer:
    """
    Gemini Vision-powered tire sidewall text extractor.

    Usage::

        analyzer = SidewallAnalyzer()
        details = await analyzer.extract(image_bytes)
        # → dict with brand, tire_size, DOT code, manufacture date, etc.
    """

    def __init__(self) -> None:
        from api_integrations.gemini.gemini_client import get_gemini_client
        self._client = get_gemini_client()

    @property
    def is_available(self) -> bool:
        return self._client.is_available()

    async def extract(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> Dict:
        """
        Extract structured tire details from a sidewall image using Gemini Vision.

        Args:
            image_bytes: Raw bytes of the sidewall photo (JPEG or PNG).
            mime_type:   MIME type — ``'image/jpeg'`` or ``'image/png'``.

        Returns:
            Dict with extracted fields (all nullable).
            Always includes ``"source"`` key:
              - ``"gemini_vision"`` on success
              - ``"unavailable"``   when API key is missing
              - ``"error"``         on API call failure
        """
        if not self.is_available:
            logger.warning("Sidewall analysis skipped — Gemini API key not configured")
            return self._empty_result("unavailable", "Gemini API key not configured")

        logger.info("Running Gemini Vision sidewall extraction (image size=%d bytes)", len(image_bytes))

        raw = await self._client.generate_with_image(
            prompt=SIDEWALL_EXTRACTION_PROMPT,
            image_bytes=image_bytes,
            mime_type=mime_type,
            temperature=0.1,    # Low temp → deterministic extraction
            # Sidewall JSON includes nested fields plus raw visible text; 1024
            # tokens can truncate the response and make otherwise-good Gemini
            # calls parse as failures.
            max_tokens=4096,
            timeout=25,
        )

        if raw is None:
            logger.warning("Gemini Vision returned no result for sidewall image")
            return self._empty_result("error", "Gemini Vision call failed or timed out")

        try:
            normalised = _normalise_result(raw)
            normalised["source"] = "gemini_vision"
            logger.info(
                "Sidewall extraction complete — brand=%s size=%s confidence=%s DOT=%s",
                normalised.get("brand"),
                normalised.get("tire_size", {}).get("full_formatted"),
                normalised.get("extraction_confidence"),
                normalised.get("dot_code", {}).get("full"),
            )
            return normalised
        except Exception as e:
            logger.error("Sidewall result normalisation failed: %s", e)
            return self._empty_result("error", f"Post-processing failed: {e}")

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_result(source: str, note: str = "") -> Dict:
        """Return a zero-filled result dict for cases where extraction is impossible."""
        return {
            "source": source,
            "brand": None,
            "tire_model": None,
            "tire_size": {
                "raw": None,
                "width_mm": None,
                "aspect_ratio": None,
                "rim_diameter_inches": None,
                "full_formatted": None,
            },
            "load_index": None,
            "speed_rating": None,
            "dot_code": {
                "full": None,
                "manufacture_week": None,
                "manufacture_year": None,
                "manufacture_date_text": None,
            },
            "construction_type": None,
            "max_pressure_psi": None,
            "max_pressure_kpa": None,
            "country_of_origin": None,
            "special_markings": [],
            "all_visible_text": None,
            "extraction_confidence": "LOW",
            "extraction_notes": note,
        }


# ── Module-level singleton ─────────────────────────────────────────────────────

_analyzer: Optional[SidewallAnalyzer] = None


def get_sidewall_analyzer() -> SidewallAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SidewallAnalyzer()
    return _analyzer
