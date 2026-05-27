"""Tire post-processing utilities.

Provides a single entrypoint `generate_tire_report` which accepts an
`image_path` and optional model/ocr outputs and returns a dict with the
fields the project expects (tread, wear class/label, health score,
remaining life, risk, replacement urgency, cleaned OCR fields, etc.).

This module implements the rules supplied in the project spec and is
pure-Python so it can be used as a deterministic post-processing step
after your models (CNN/ANN/OCR) produce predictions.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Optional, Tuple

NEW_TREAD_MM = 8.0
LEGAL_MIN_TREAD_MM = 1.6

WEAR_LABELS = {
    0: "Excellent",
    1: "Good",
    2: "Moderate",
    3: "Poor",
    4: "Critical",
}

FORM_TO_PERCENT = {
    "excellent": 100,
    "good": 80,
    "moderate": 60,
    "poor": 40,
    "critical": 20,
}

OCR_CONFIDENCE_MAP = {
    "clear": 0.95,
    "slight blur": 0.85,
    "medium blur": 0.70,
    "hard to read": 0.50,
    "very poor": 0.30,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def wear_class_and_label_from_tread(tread_mm: Optional[float]) -> Tuple[Optional[int], Optional[str]]:
    if tread_mm is None:
        return None, None
    if tread_mm > 7.0:
        c = 0
    elif tread_mm >= 5.5:
        c = 1
    elif tread_mm >= 3.5:
        c = 2
    elif tread_mm >= 2.0:
        c = 3
    else:
        c = 4
    return c, WEAR_LABELS[c]


def tread_percent(tread_mm: Optional[float]) -> float:
    if tread_mm is None:
        return 0.0
    return _clamp((tread_mm / NEW_TREAD_MM) * 100.0)


def shape_percent_from_form(value: Optional[Any]) -> float:
    if value is None:
        return 60.0
    if isinstance(value, (int, float)):
        return _clamp(float(value))
    s = str(value).strip().lower()
    return FORM_TO_PERCENT.get(s, 60.0)


def surface_percent_from_inputs(wear_pattern: Optional[str], crack_detected: bool, surface_texture: Optional[str]) -> float:
    if crack_detected:
        # visible cracks penalize strongly
        if wear_pattern and ("severe" in wear_pattern.lower() or "tear" in wear_pattern.lower()):
            return 10.0
        return 30.0
    if surface_texture:
        st = surface_texture.lower()
        if "smooth" in st:
            return 100.0
        if "minor" in st:
            return 80.0
        if "uneven" in st:
            return 60.0
        if "crack" in st:
            return 30.0
    if wear_pattern:
        wp = wear_pattern.lower()
        if "minor" in wp:
            return 80.0
        if "uneven" in wp or "unequal" in wp:
            return 60.0
        if "severe" in wp:
            return 10.0
    return 100.0


def health_score_from_parts(tread_mm: Optional[float], average_form: Optional[Any], wear_pattern: Optional[str], crack_detected: bool, surface_texture: Optional[str]) -> float:
    t_pct = tread_percent(tread_mm)
    s_pct = shape_percent_from_form(average_form)
    surf_pct = surface_percent_from_inputs(wear_pattern, crack_detected, surface_texture)
    score = 0.5 * t_pct + 0.3 * s_pct + 0.2 * surf_pct
    return _clamp(round(score, 2))


def remaining_life_percent(tread_mm: Optional[float]) -> float:
    if tread_mm is None:
        return 0.0
    if tread_mm <= LEGAL_MIN_TREAD_MM:
        return 0.0
    denom = NEW_TREAD_MM - LEGAL_MIN_TREAD_MM
    numer = tread_mm - LEGAL_MIN_TREAD_MM
    return _clamp((numer / denom) * 100.0)


def replacement_urgency_from_remaining_life(remaining_pct: float) -> str:
    if remaining_pct > 70:
        return "Low"
    if remaining_pct >= 40:
        return "Medium"
    if remaining_pct >= 20:
        return "High"
    return "Immediate"


def risk_score_and_level(remaining_pct: float, crack_detected: bool, wear_pattern: Optional[str], manufacture_year: Optional[int], current_year: Optional[int]) -> Tuple[int, str]:
    # Components: tread (50%), cracks (25%), wear pattern (15%), age (10%)
    tread_comp = 100.0 - remaining_pct
    crack_comp = 100.0 if crack_detected else 0.0
    wp_comp = 0.0
    if wear_pattern:
        wp = wear_pattern.lower()
        if "uneven" in wp or "edge" in wp or "severe" in wp:
            wp_comp = 100.0
        elif "minor" in wp:
            wp_comp = 50.0
        else:
            wp_comp = 0.0

    age_comp = 0.0
    cur = current_year or datetime.datetime.now().year
    if manufacture_year:
        age = cur - manufacture_year
        age_comp = _clamp((min(age, 20) / 20.0) * 100.0)

    score = 0.5 * tread_comp + 0.25 * crack_comp + 0.15 * wp_comp + 0.10 * age_comp
    score = int(_clamp(round(score)))
    if score <= 25:
        level = "Safe"
    elif score <= 50:
        level = "Monitor"
    elif score <= 75:
        level = "Warning"
    else:
        level = "Dangerous"
    return score, level


def clean_brand(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = re.sub(r'[^A-Za-z0-9]', '', raw).upper()
    return cleaned or None


def clean_tire_size(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip()
    # flexible regex to capture width/aspect/rim
    m = re.search(r"(\d{2,3})\D{0,3}(\d{2})\D{0,3}R?\s*(\d{2})", s, flags=re.I)
    if m:
        width, aspect, rim = m.groups()
        return f"{width}/{aspect}R{rim}"
    # fallback: normalize common separators
    s2 = re.sub(r"[\s\-]+", "", s, flags=re.I)
    s2 = s2.upper().replace('R', 'R')
    # crude check
    if re.match(r"^\d{2,3}/\d{2}R\d{2}$", s2):
        return s2
    return None


def parse_dot_dom(raw: Optional[str], current_year: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
    if not raw:
        return None, None
    m = re.search(r'(?:DOT\s*)?(\d{4})', raw, flags=re.I)
    if not m:
        return None, None
    digits = m.group(1)
    week = int(digits[:2])
    year_short = int(digits[2:])
    cur = current_year or datetime.datetime.now().year
    # map two-digit year -> 19xx/20xx using current year heuristic
    if 2000 + year_short <= cur:
        year = 2000 + year_short
    else:
        year = 1900 + year_short
    return week, year


def parse_ocr_confidence(value: Optional[Any]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if 0.0 <= v <= 1.0:
            return round(v, 2)
        # assume 0-100
        if 0.0 <= v <= 100.0:
            return round(v / 100.0, 2)
    s = str(value).strip().lower()
    return OCR_CONFIDENCE_MAP.get(s)


def generate_tire_report(image_path: str, *, model_outputs: Optional[Dict[str, Any]] = None, ocr_text: Optional[str] = None, ocr_confidence: Optional[Any] = None, current_year: Optional[int] = None) -> Dict[str, Any]:
    """Produce a dictionary with the standard tire fields.

    model_outputs can contain keys produced by your ML pipeline (for
    example `tread_depth_pred`, `wear_pattern_pred`, `crack_detected`,
    `average_form`, `surface_texture`, `groove_visible`, `confidence`,
    `brand_raw`, `tire_size_raw`, `dot_raw`). If a value is missing the
    function will fall back to reasonable defaults.
    """
    mo = model_outputs or {}
    current_year = current_year or datetime.datetime.now().year

    tread_depth_mm = mo.get('tread_depth_pred')
    wear_pattern = mo.get('wear_pattern_pred')
    crack_detected = bool(mo.get('crack_detected', False))
    average_form = mo.get('average_form') or mo.get('shape')
    surface_texture = mo.get('surface_texture')
    groove_visible = mo.get('groove_visible')
    confidence = mo.get('confidence') or parse_ocr_confidence(ocr_confidence) or 1.0

    brand_raw = mo.get('brand_raw')
    tire_size_raw = mo.get('tire_size_raw')
    dot_raw = mo.get('dot_raw') or (ocr_text or '')

    # OCR fallbacks: try to extract simple fields from provided ocr_text
    if ocr_text:
        text = ocr_text
        if not brand_raw:
            # try simple brand extraction heuristics (first all-caps word)
            m = re.search(r"\b([A-Z0-9]{2,})\b", ocr_text)
            if m:
                brand_raw = m.group(1)
        if not tire_size_raw:
            m2 = re.search(r"(\d{2,3}\s*[\/-]?\s*\d{2}\s*[Rr]?\s*\d{2})", ocr_text)
            if m2:
                tire_size_raw = m2.group(1)

    brand_cleaned = clean_brand(brand_raw)
    tire_size_cleaned = clean_tire_size(tire_size_raw)

    manufact_week, manufact_year = parse_dot_dom(dot_raw, current_year=current_year)

    wear_class, wear_label = wear_class_and_label_from_tread(tread_depth_mm)
    health_score = health_score_from_parts(tread_depth_mm, average_form, wear_pattern, crack_detected, surface_texture)
    remaining_life = remaining_life_percent(tread_depth_mm)
    replacement_urgency = replacement_urgency_from_remaining_life(remaining_life)
    risk_score, risk_level = risk_score_and_level(remaining_life, crack_detected, wear_pattern, manufact_year, current_year)

    # Age-based adjustments
    tire_age = None
    if manufact_year:
        tire_age = current_year - manufact_year
        if tire_age > 5:
            # small heuristic adjustments: older tires are riskier
            health_score = _clamp(health_score - 10.0)
            risk_score = min(100, risk_score + 10)
            # bump urgency one level
            order = ['Low', 'Medium', 'High', 'Immediate']
            try:
                idx = order.index(replacement_urgency)
                replacement_urgency = order[min(len(order) - 1, idx + 1)]
            except ValueError:
                pass

    report: Dict[str, Any] = {
        'image_path': image_path,
        'tread_depth_pred': tread_depth_mm,
        'tread_depth_mm': tread_depth_mm,
        'wear_pattern_pred': wear_pattern,
        'wear_class': wear_class,
        'wear_label': wear_label,
        'health_score_pred': health_score,
        'remaining_life_pred': round(remaining_life, 2),
        'replacement_urgency': replacement_urgency,
        'risk_level': risk_level,
        'risk_score': risk_score,
        'crack_detected': crack_detected,
        'groove_visible': groove_visible,
        'surface_texture': surface_texture,
        'confidence': round(float(confidence), 3) if confidence is not None else None,
        'brand_raw': brand_raw,
        'brand_cleaned': brand_cleaned,
        'tire_size_raw': tire_size_raw,
        'tire_size_cleaned': tire_size_cleaned,
        'manufacture_week': manufact_week,
        'manufacture_year': manufact_year,
        'tire_age_years': tire_age,
        'ocr_confidence': parse_ocr_confidence(ocr_confidence),
    }

    return report


__all__ = ["generate_tire_report"]
