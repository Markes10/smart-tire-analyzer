"""
Smart Tire Analyzer — Unified Class Definitions
================================================
All classification labels used across the entire system, organised into
three levels:

  Level 1 — AI Model Classes      (CNN + Transformer + RNN + ANN outputs)
  Level 2 — Road / Context Classes (Google Maps + Weather API)
  Level 3 — Final Output Classes   (User-facing report)

Usage::

    from ai_model.classes import (
        TireHealthClass, TreadDepthClass, WearPatternClass, TireDamageClass,
        RoadConditionClass, WeatherConditionClass,
        DrivingRiskClass, DrivingAdviceClass,
        ContinuousLearningClass, ModelConfidenceClass,
        classify_tread_depth, classify_health, classify_confidence,
        tread_to_condition, risk_from_combined,
        WEAR_LABEL_TO_CLASS, WEAR_CLASS_TO_LABEL,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 1 — AI MODEL CLASSES
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Tire Health Classes ─────────────────────────────────────────────────────

@unique
class TireHealthClass(str, Enum):
    """
    Overall tire health bucket — output of the ANN prediction head.
    Maps directly to a health_score range (0-10).

    Used by: CNN feature head, ANN output, ReportService
    """
    NEW_TIRE    = "new_tire"          # health_score 9.0 – 10.0
    GOOD        = "good_condition"    # health_score 7.0 – 8.9
    MODERATE    = "moderate_wear"     # health_score 5.0 – 6.9
    HEAVY_WEAR  = "heavy_wear"        # health_score 3.0 – 4.9
    REPLACE_SOON = "replace_soon"     # health_score 1.6 – 2.9
    CRITICAL    = "critical_dangerous" # health_score < 1.6

    @property
    def label(self) -> str:
        return _HEALTH_LABELS[self]

    @property
    def score_range(self) -> Tuple[float, float]:
        return _HEALTH_SCORE_RANGES[self]


_HEALTH_LABELS: Dict[TireHealthClass, str] = {
    TireHealthClass.NEW_TIRE:     "New Tire",
    TireHealthClass.GOOD:         "Good Condition",
    TireHealthClass.MODERATE:     "Moderate Wear",
    TireHealthClass.HEAVY_WEAR:   "Heavy Wear",
    TireHealthClass.REPLACE_SOON: "Replace Soon",
    TireHealthClass.CRITICAL:     "Critical / Dangerous",
}

_HEALTH_SCORE_RANGES: Dict[TireHealthClass, Tuple[float, float]] = {
    TireHealthClass.NEW_TIRE:     (9.0, 10.0),
    TireHealthClass.GOOD:         (7.0,  8.9),
    TireHealthClass.MODERATE:     (5.0,  6.9),
    TireHealthClass.HEAVY_WEAR:   (3.0,  4.9),
    TireHealthClass.REPLACE_SOON: (1.6,  2.9),
    TireHealthClass.CRITICAL:     (0.0,  1.59),
}


def classify_health(score: float) -> TireHealthClass:
    """Map a health_score (0–10) to a TireHealthClass."""
    if score >= 9.0:
        return TireHealthClass.NEW_TIRE
    if score >= 7.0:
        return TireHealthClass.GOOD
    if score >= 5.0:
        return TireHealthClass.MODERATE
    if score >= 3.0:
        return TireHealthClass.HEAVY_WEAR
    if score >= 1.6:
        return TireHealthClass.REPLACE_SOON
    return TireHealthClass.CRITICAL


# ── 2. Tread Depth Classes ─────────────────────────────────────────────────────

@unique
class TreadDepthClass(str, Enum):
    """
    Tread depth classification bucket.
    The model predicts a continuous value (0–12 mm) AND this discrete bucket.

    Used by: ANN output head, ReportService, Alert engine
    """
    NEW        = "new"          # > 8 mm
    GOOD       = "good"         # 6 – 8 mm
    MODERATE   = "moderate"     # 4 – 6 mm
    REPLACE_SOON = "replace_soon"  # 2 – 4 mm
    DANGEROUS  = "dangerous"    # < 2 mm

    @property
    def label(self) -> str:
        return _TREAD_LABELS[self]

    @property
    def mm_range(self) -> Tuple[float, float]:
        return _TREAD_MM_RANGES[self]

    @property
    def is_safe(self) -> bool:
        return self in (TreadDepthClass.NEW, TreadDepthClass.GOOD, TreadDepthClass.MODERATE)


_TREAD_LABELS: Dict[TreadDepthClass, str] = {
    TreadDepthClass.NEW:          "New (> 8 mm)",
    TreadDepthClass.GOOD:         "Good (6 – 8 mm)",
    TreadDepthClass.MODERATE:     "Moderate (4 – 6 mm)",
    TreadDepthClass.REPLACE_SOON: "Replace Soon (2 – 4 mm)",
    TreadDepthClass.DANGEROUS:    "Dangerous (< 2 mm)",
}

_TREAD_MM_RANGES: Dict[TreadDepthClass, Tuple[float, float]] = {
    TreadDepthClass.NEW:          (8.0, 12.0),
    TreadDepthClass.GOOD:         (6.0,  8.0),
    TreadDepthClass.MODERATE:     (4.0,  6.0),
    TreadDepthClass.REPLACE_SOON: (2.0,  4.0),
    TreadDepthClass.DANGEROUS:    (0.0,  2.0),
}


def classify_tread_depth(mm: float) -> TreadDepthClass:
    """Map a tread depth in mm to a TreadDepthClass."""
    if mm > 8.0:
        return TreadDepthClass.NEW
    if mm >= 6.0:
        return TreadDepthClass.GOOD
    if mm >= 4.0:
        return TreadDepthClass.MODERATE
    if mm >= 2.0:
        return TreadDepthClass.REPLACE_SOON
    return TreadDepthClass.DANGEROUS


# ── 3. Wear Pattern Classes ────────────────────────────────────────────────────

@unique
class WearPatternClass(str, Enum):
    """
    Wear pattern type — detected by CNN + Vision Transformer.
    Indicates both the wear type and likely root cause.

    Used by: CNN, Transformer encoder, ANN output, Alert engine
    """
    EVEN_WEAR       = "even_wear"
    CENTER_WEAR     = "center_wear"
    EDGE_WEAR       = "edge_wear"
    ONE_SIDE_WEAR   = "one_side_wear"
    CUPPING_WEAR    = "cupping_wear"
    FEATHERING_WEAR = "feathering_wear"
    PATCH_WEAR      = "patch_wear"

    @property
    def label(self) -> str:
        return _WEAR_LABELS[self]

    @property
    def cause(self) -> str:
        return _WEAR_CAUSES[self]

    @property
    def advice(self) -> str:
        return _WEAR_ADVICE[self]


_WEAR_LABELS: Dict[WearPatternClass, str] = {
    WearPatternClass.EVEN_WEAR:       "Even Wear",
    WearPatternClass.CENTER_WEAR:     "Center Wear",
    WearPatternClass.EDGE_WEAR:       "Edge Wear",
    WearPatternClass.ONE_SIDE_WEAR:   "One Side Wear",
    WearPatternClass.CUPPING_WEAR:    "Cupping / Scalloping Wear",
    WearPatternClass.FEATHERING_WEAR: "Feathering Wear",
    WearPatternClass.PATCH_WEAR:      "Patch / Spotty Wear",
}

_WEAR_CAUSES: Dict[WearPatternClass, str] = {
    WearPatternClass.EVEN_WEAR:       "Normal wear — proper inflation and alignment",
    WearPatternClass.CENTER_WEAR:     "Over-inflation — center contacts road more",
    WearPatternClass.EDGE_WEAR:       "Under-inflation — edges contact road more",
    WearPatternClass.ONE_SIDE_WEAR:   "Camber misalignment or worn suspension",
    WearPatternClass.CUPPING_WEAR:    "Worn shock absorbers or loose suspension",
    WearPatternClass.FEATHERING_WEAR: "Toe misalignment",
    WearPatternClass.PATCH_WEAR:      "Wheel imbalance or brake grab",
}

_WEAR_ADVICE: Dict[WearPatternClass, str] = {
    WearPatternClass.EVEN_WEAR:       "Continue regular monitoring.",
    WearPatternClass.CENTER_WEAR:     "Reduce tire inflation pressure to recommended level.",
    WearPatternClass.EDGE_WEAR:       "Increase tire inflation pressure to recommended level.",
    WearPatternClass.ONE_SIDE_WEAR:   "Have camber angle checked and adjusted.",
    WearPatternClass.CUPPING_WEAR:    "Inspect shock absorbers and suspension components.",
    WearPatternClass.FEATHERING_WEAR: "Check and adjust toe alignment.",
    WearPatternClass.PATCH_WEAR:      "Balance wheels and check brake callipers.",
}

# Integer class_id ↔ WearPatternClass mappings (for model output tensor)
WEAR_CLASS_ID_MAP: Dict[int, WearPatternClass] = {
    0: WearPatternClass.CENTER_WEAR,
    1: WearPatternClass.EDGE_WEAR,
    2: WearPatternClass.PATCH_WEAR,
    3: WearPatternClass.EVEN_WEAR,
    4: WearPatternClass.ONE_SIDE_WEAR,
    5: WearPatternClass.CUPPING_WEAR,
    6: WearPatternClass.FEATHERING_WEAR,
}
WEAR_CLASS_ID_REVERSE: Dict[WearPatternClass, int] = {v: k for k, v in WEAR_CLASS_ID_MAP.items()}

# String label ↔ WearPatternClass (for CSV / API compatibility)
WEAR_LABEL_TO_CLASS: Dict[str, WearPatternClass] = {c.value: c for c in WearPatternClass}
WEAR_CLASS_TO_LABEL: Dict[WearPatternClass, str] = {c: c.value for c in WearPatternClass}

NUM_WEAR_CLASSES = len(WearPatternClass)


# ── 4. Tire Damage Classes ─────────────────────────────────────────────────────

@unique
class TireDamageClass(str, Enum):
    """
    Physical damage detected from the tire image.
    Separate from wear pattern — damage requires immediate action.

    Used by: CNN damage head, Alert engine
    """
    NO_DAMAGE        = "no_damage"
    CRACK            = "crack"
    CUT              = "cut"
    BULGE            = "bulge"
    PUNCTURE         = "puncture"
    SIDEWALL_DAMAGE  = "sidewall_damage"
    UNEVEN_SURFACE   = "uneven_surface"

    @property
    def label(self) -> str:
        return _DAMAGE_LABELS[self]

    @property
    def is_critical(self) -> bool:
        """Damage types that make the tire immediately unsafe."""
        return self in (
            TireDamageClass.BULGE,
            TireDamageClass.SIDEWALL_DAMAGE,
            TireDamageClass.PUNCTURE,
        )


_DAMAGE_LABELS: Dict[TireDamageClass, str] = {
    TireDamageClass.NO_DAMAGE:       "No Damage",
    TireDamageClass.CRACK:           "Crack",
    TireDamageClass.CUT:             "Cut",
    TireDamageClass.BULGE:           "Bulge",
    TireDamageClass.PUNCTURE:        "Puncture",
    TireDamageClass.SIDEWALL_DAMAGE: "Sidewall Damage",
    TireDamageClass.UNEVEN_SURFACE:  "Uneven Surface",
}

DAMAGE_CLASS_ID_MAP: Dict[int, TireDamageClass] = {
    i: cls for i, cls in enumerate(TireDamageClass)
}
NUM_DAMAGE_CLASSES = len(TireDamageClass)


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 2 — ROAD / CONTEXT CLASSES
# ══════════════════════════════════════════════════════════════════════════════

# ── 5. Road Condition Classes ──────────────────────────────────────────────────

@unique
class RoadConditionClass(str, Enum):
    """
    Road surface condition inferred from Google Maps / Street View data.
    Affects the road_wear_multiplier applied to remaining life estimate.

    Used by: MapsService, Context Intelligence Layer
    """
    SMOOTH       = "smooth_road"        # multiplier 1.0
    SLIGHTLY_ROUGH = "slightly_rough"   # multiplier 1.15
    ROUGH        = "rough_road"         # multiplier 1.35
    POTHOLES     = "potholes"           # multiplier 1.60
    GRAVEL       = "gravel_road"        # multiplier 1.50
    MUD          = "mud_road"           # multiplier 1.40
    WET          = "wet_road"           # multiplier 1.20
    SNOW         = "snow_road"          # multiplier 1.30
    CONSTRUCTION = "construction_road"  # multiplier 1.45

    @property
    def label(self) -> str:
        return _ROAD_LABELS[self]

    @property
    def wear_multiplier(self) -> float:
        """How much faster this road surface degrades tires relative to smooth."""
        return _ROAD_WEAR_MULTIPLIERS[self]


_ROAD_LABELS: Dict[RoadConditionClass, str] = {
    RoadConditionClass.SMOOTH:         "Smooth Road",
    RoadConditionClass.SLIGHTLY_ROUGH: "Slightly Rough",
    RoadConditionClass.ROUGH:          "Rough Road",
    RoadConditionClass.POTHOLES:       "Potholes",
    RoadConditionClass.GRAVEL:         "Gravel Road",
    RoadConditionClass.MUD:            "Mud Road",
    RoadConditionClass.WET:            "Wet Road",
    RoadConditionClass.SNOW:           "Snow Road",
    RoadConditionClass.CONSTRUCTION:   "Construction Road",
}

_ROAD_WEAR_MULTIPLIERS: Dict[RoadConditionClass, float] = {
    RoadConditionClass.SMOOTH:         1.00,
    RoadConditionClass.WET:            1.20,
    RoadConditionClass.SLIGHTLY_ROUGH: 1.15,
    RoadConditionClass.SNOW:           1.30,
    RoadConditionClass.ROUGH:          1.35,
    RoadConditionClass.MUD:            1.40,
    RoadConditionClass.CONSTRUCTION:   1.45,
    RoadConditionClass.GRAVEL:         1.50,
    RoadConditionClass.POTHOLES:       1.60,
}

ROAD_LABEL_TO_CLASS: Dict[str, RoadConditionClass] = {c.value: c for c in RoadConditionClass}


# ── 6. Weather Condition Classes ───────────────────────────────────────────────

@unique
class WeatherConditionClass(str, Enum):
    """
    Weather condition from OpenWeatherMap API.
    Affects risk level and driving advice.

    Used by: WeatherService, Risk engine, Gemini prompt
    """
    DRY         = "dry"
    RAIN        = "rain"
    HEAVY_RAIN  = "heavy_rain"
    FOG         = "fog"
    SNOW        = "snow"
    HOT         = "hot_weather"
    COLD        = "cold_weather"

    @property
    def label(self) -> str:
        return _WEATHER_LABELS[self]

    @property
    def risk_multiplier(self) -> float:
        return _WEATHER_RISK_MULTIPLIERS[self]

    @property
    def requires_caution(self) -> bool:
        return self in (
            WeatherConditionClass.RAIN,
            WeatherConditionClass.HEAVY_RAIN,
            WeatherConditionClass.FOG,
            WeatherConditionClass.SNOW,
        )


_WEATHER_LABELS: Dict[WeatherConditionClass, str] = {
    WeatherConditionClass.DRY:        "Dry",
    WeatherConditionClass.RAIN:       "Rain",
    WeatherConditionClass.HEAVY_RAIN: "Heavy Rain",
    WeatherConditionClass.FOG:        "Fog",
    WeatherConditionClass.SNOW:       "Snow",
    WeatherConditionClass.HOT:        "Hot Weather",
    WeatherConditionClass.COLD:       "Cold Weather",
}

_WEATHER_RISK_MULTIPLIERS: Dict[WeatherConditionClass, float] = {
    WeatherConditionClass.DRY:        1.00,
    WeatherConditionClass.HOT:        1.10,
    WeatherConditionClass.COLD:       1.10,
    WeatherConditionClass.FOG:        1.15,
    WeatherConditionClass.RAIN:       1.25,
    WeatherConditionClass.SNOW:       1.45,
    WeatherConditionClass.HEAVY_RAIN: 1.40,
}

WEATHER_LABEL_TO_CLASS: Dict[str, WeatherConditionClass] = {c.value: c for c in WeatherConditionClass}


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 3 — FINAL OUTPUT CLASSES (USER-FACING)
# ══════════════════════════════════════════════════════════════════════════════

# ── 7. Driving Risk Classes ────────────────────────────────────────════════════

@unique
class DrivingRiskClass(str, Enum):
    """
    Combined driving risk level output.
    Computed from: Tire Condition + Road Condition + Weather.

    Used by: ReportService, Gemini prompt, Alert engine
    """
    LOW      = "low_risk"
    MODERATE = "moderate_risk"
    HIGH     = "high_risk"
    CRITICAL = "critical_risk"

    @property
    def label(self) -> str:
        return _RISK_LABELS[self]

    @property
    def colour(self) -> str:
        """Hex colour for UI display."""
        return _RISK_COLOURS[self]

    @property
    def api_value(self) -> str:
        """Legacy string used in API responses (uppercase short form)."""
        return self.name  # "LOW" | "MODERATE" | "HIGH" | "CRITICAL"


_RISK_LABELS: Dict[DrivingRiskClass, str] = {
    DrivingRiskClass.LOW:      "Low Risk",
    DrivingRiskClass.MODERATE: "Moderate Risk",
    DrivingRiskClass.HIGH:     "High Risk",
    DrivingRiskClass.CRITICAL: "Critical Risk",
}

_RISK_COLOURS: Dict[DrivingRiskClass, str] = {
    DrivingRiskClass.LOW:      "#22c55e",  # green-500
    DrivingRiskClass.MODERATE: "#f59e0b",  # amber-500
    DrivingRiskClass.HIGH:     "#ef4444",  # red-500
    DrivingRiskClass.CRITICAL: "#7f1d1d",  # red-900
}

RISK_LABEL_TO_CLASS: Dict[str, DrivingRiskClass] = {
    "LOW": DrivingRiskClass.LOW,
    "MODERATE": DrivingRiskClass.MODERATE,
    "HIGH": DrivingRiskClass.HIGH,
    "CRITICAL": DrivingRiskClass.CRITICAL,
}


def risk_from_combined(
    health_class: TireHealthClass,
    road_class: RoadConditionClass,
    weather_class: WeatherConditionClass,
) -> DrivingRiskClass:
    """
    Compute combined DrivingRiskClass from all three context tiers.

    Uses multiplicative risk scoring:
      base_risk (from tire health) × road_wear × weather_risk → thresholds.
    """
    _base: Dict[TireHealthClass, float] = {
        TireHealthClass.NEW_TIRE:     1.0,
        TireHealthClass.GOOD:         1.2,
        TireHealthClass.MODERATE:     1.5,
        TireHealthClass.HEAVY_WEAR:   2.0,
        TireHealthClass.REPLACE_SOON: 3.0,
        TireHealthClass.CRITICAL:     5.0,
    }
    score = (
        _base[health_class]
        * road_class.wear_multiplier
        * weather_class.risk_multiplier
    )
    if score >= 4.0:
        return DrivingRiskClass.CRITICAL
    if score >= 2.5:
        return DrivingRiskClass.HIGH
    if score >= 1.5:
        return DrivingRiskClass.MODERATE
    return DrivingRiskClass.LOW


# ── 8. Driving Advice Classes ──────────────────────────────────────────────────

@unique
class DrivingAdviceClass(str, Enum):
    """
    Actionable driving advice — produced by Gemini AI or rule-based fallback.
    Multiple advice items can be active simultaneously.

    Used by: GeminiService, ReportService, Alert engine
    """
    SAFE_TO_DRIVE     = "safe_to_drive"
    DRIVE_CAREFULLY   = "drive_carefully"
    REDUCE_SPEED      = "reduce_speed"
    AVOID_HIGHWAY     = "avoid_highway"
    REPLACE_TIRE_SOON = "replace_tire_soon"
    DO_NOT_DRIVE      = "do_not_drive"

    @property
    def label(self) -> str:
        return _ADVICE_LABELS[self]

    @property
    def priority(self) -> int:
        """Lower number = shown first in UI."""
        return _ADVICE_PRIORITY[self]


_ADVICE_LABELS: Dict[DrivingAdviceClass, str] = {
    DrivingAdviceClass.SAFE_TO_DRIVE:     "Safe to Drive",
    DrivingAdviceClass.DRIVE_CAREFULLY:   "Drive Carefully",
    DrivingAdviceClass.REDUCE_SPEED:      "Reduce Speed",
    DrivingAdviceClass.AVOID_HIGHWAY:     "Avoid Highway",
    DrivingAdviceClass.REPLACE_TIRE_SOON: "Replace Tire Soon",
    DrivingAdviceClass.DO_NOT_DRIVE:      "Do Not Drive",
}

_ADVICE_PRIORITY: Dict[DrivingAdviceClass, int] = {
    DrivingAdviceClass.DO_NOT_DRIVE:      1,
    DrivingAdviceClass.REPLACE_TIRE_SOON: 2,
    DrivingAdviceClass.AVOID_HIGHWAY:     3,
    DrivingAdviceClass.REDUCE_SPEED:      4,
    DrivingAdviceClass.DRIVE_CAREFULLY:   5,
    DrivingAdviceClass.SAFE_TO_DRIVE:     6,
}


def advice_from_risk(risk: DrivingRiskClass) -> List[DrivingAdviceClass]:
    """Return ordered list of advice items for a given risk level."""
    _map: Dict[DrivingRiskClass, List[DrivingAdviceClass]] = {
        DrivingRiskClass.LOW: [
            DrivingAdviceClass.SAFE_TO_DRIVE,
        ],
        DrivingRiskClass.MODERATE: [
            DrivingAdviceClass.DRIVE_CAREFULLY,
            DrivingAdviceClass.REDUCE_SPEED,
        ],
        DrivingRiskClass.HIGH: [
            DrivingAdviceClass.REDUCE_SPEED,
            DrivingAdviceClass.AVOID_HIGHWAY,
            DrivingAdviceClass.REPLACE_TIRE_SOON,
        ],
        DrivingRiskClass.CRITICAL: [
            DrivingAdviceClass.DO_NOT_DRIVE,
            DrivingAdviceClass.REPLACE_TIRE_SOON,
        ],
    }
    return sorted(_map.get(risk, [DrivingAdviceClass.DRIVE_CAREFULLY]), key=lambda a: a.priority)


# ── 9. Continuous Learning Classes ────────────────────────────────────────────

@unique
class ContinuousLearningClass(str, Enum):
    """
    Status label assigned to a prediction by the Self-Correcting Learning Engine.
    Controls whether the sample is queued for retraining.

    Used by: feedback_service.py, Self-Correcting Engine, Retraining pipeline
    """
    CORRECT_PREDICTION = "correct_prediction"
    LOW_CONFIDENCE     = "low_confidence"
    WRONG_PREDICTION   = "wrong_prediction"
    NEEDS_RETRAINING   = "needs_retraining"
    VERIFIED_DATA      = "verified_data"

    @property
    def label(self) -> str:
        return _CL_LABELS[self]

    @property
    def should_retrain(self) -> bool:
        return self in (
            ContinuousLearningClass.WRONG_PREDICTION,
            ContinuousLearningClass.NEEDS_RETRAINING,
            ContinuousLearningClass.LOW_CONFIDENCE,
        )


_CL_LABELS: Dict[ContinuousLearningClass, str] = {
    ContinuousLearningClass.CORRECT_PREDICTION: "Correct Prediction",
    ContinuousLearningClass.LOW_CONFIDENCE:     "Low Confidence",
    ContinuousLearningClass.WRONG_PREDICTION:   "Wrong Prediction",
    ContinuousLearningClass.NEEDS_RETRAINING:   "Needs Retraining",
    ContinuousLearningClass.VERIFIED_DATA:      "Verified Data",
}


# ── 10. Model Confidence Classes ───────────────────────────────────────────────

@unique
class ModelConfidenceClass(str, Enum):
    """
    Confidence tier for any model prediction.
    Low confidence triggers the Self-Correcting Learning Engine.

    High:   confidence ≥ 0.90
    Medium: confidence  0.70 – 0.89
    Low:    confidence < 0.70
    """
    HIGH   = "high_confidence"    # ≥ 90%  — accept prediction directly
    MEDIUM = "medium_confidence"  # 70-90% — flag for review
    LOW    = "low_confidence"     # < 70%  — trigger self-correcting engine

    @property
    def label(self) -> str:
        return _CONF_LABELS[self]

    @property
    def threshold(self) -> float:
        return _CONF_THRESHOLDS[self]

    @property
    def triggers_self_correction(self) -> bool:
        return self == ModelConfidenceClass.LOW


_CONF_LABELS: Dict[ModelConfidenceClass, str] = {
    ModelConfidenceClass.HIGH:   "High Confidence (> 90%)",
    ModelConfidenceClass.MEDIUM: "Medium Confidence (70 – 90%)",
    ModelConfidenceClass.LOW:    "Low Confidence (< 70%)",
}

_CONF_THRESHOLDS: Dict[ModelConfidenceClass, float] = {
    ModelConfidenceClass.HIGH:   0.90,
    ModelConfidenceClass.MEDIUM: 0.70,
    ModelConfidenceClass.LOW:    0.00,
}


def classify_confidence(score: float) -> ModelConfidenceClass:
    """Map a model confidence score (0.0–1.0) to a ModelConfidenceClass."""
    if score >= 0.90:
        return ModelConfidenceClass.HIGH
    if score >= 0.70:
        return ModelConfidenceClass.MEDIUM
    return ModelConfidenceClass.LOW


# ══════════════════════════════════════════════════════════════════════════════
# COMBINED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def tread_to_condition(mm: float) -> str:
    """Return human-readable condition string for a tread depth in mm."""
    return classify_tread_depth(mm).label


@dataclass
class SmartTireReport:
    """
    Final user-facing Smart Tire Report — combines all class outputs.

    Example::

        SmartTireReport(
            tire_condition    = TireHealthClass.MODERATE,
            tread_depth_mm    = 3.2,
            tread_class       = TreadDepthClass.REPLACE_SOON,
            wear_pattern      = WearPatternClass.EDGE_WEAR,
            damage            = TireDamageClass.NO_DAMAGE,
            road_condition    = RoadConditionClass.ROUGH,
            weather           = WeatherConditionClass.RAIN,
            risk_level        = DrivingRiskClass.HIGH,
            advice            = [DrivingAdviceClass.REDUCE_SPEED,
                                 DrivingAdviceClass.REPLACE_TIRE_SOON],
            learning_status   = ContinuousLearningClass.CORRECT_PREDICTION,
            confidence        = ModelConfidenceClass.HIGH,
        )
    """
    # ── Tier 1 (AI model outputs) ──────────────────────────────────────────
    tire_condition:   TireHealthClass
    tread_depth_mm:   float
    tread_class:      TreadDepthClass
    wear_pattern:     WearPatternClass
    damage:           TireDamageClass         = TireDamageClass.NO_DAMAGE

    # ── Tier 2 (Context) ───────────────────────────────────────────────────
    road_condition:   RoadConditionClass      = RoadConditionClass.SMOOTH
    weather:          WeatherConditionClass   = WeatherConditionClass.DRY

    # ── Tier 3 (Final output) ──────────────────────────────────────────────
    risk_level:       DrivingRiskClass        = DrivingRiskClass.LOW
    advice:           List[DrivingAdviceClass] = field(default_factory=list)

    # ── Meta ───────────────────────────────────────────────────────────────
    learning_status:  ContinuousLearningClass = ContinuousLearningClass.CORRECT_PREDICTION
    confidence:       ModelConfidenceClass    = ModelConfidenceClass.HIGH

    def to_summary(self) -> str:
        """One-line human-readable summary."""
        advice_str = " | ".join(a.label for a in self.advice)
        return (
            f"Tire: {self.tire_condition.label} | "
            f"Tread: {self.tread_depth_mm:.1f}mm ({self.tread_class.label}) | "
            f"Wear: {self.wear_pattern.label} | "
            f"Road: {self.road_condition.label} | "
            f"Weather: {self.weather.label} | "
            f"Risk: {self.risk_level.label} | "
            f"Advice: {advice_str}"
        )

    def to_dict(self) -> Dict:
        """Serialise to JSON-ready dict for API response."""
        return {
            "tire_condition":  self.tire_condition.label,
            "tread_depth_mm":  round(self.tread_depth_mm, 2),
            "tread_class":     self.tread_class.label,
            "wear_pattern":    self.wear_pattern.label,
            "wear_cause":      self.wear_pattern.cause,
            "wear_advice":     self.wear_pattern.advice,
            "damage":          self.damage.label,
            "road_condition":  self.road_condition.label,
            "weather":         self.weather.label,
            "risk_level":      self.risk_level.label,
            "risk_colour":     self.risk_level.colour,
            "advice":          [a.label for a in self.advice],
            "learning_status": self.learning_status.label,
            "confidence":      self.confidence.label,
        }


def build_smart_tire_report(
    health_score: float,
    tread_depth_mm: float,
    wear_label: str,
    damage_label: str = "no_damage",
    road_condition_label: str = "smooth_road",
    weather_label: str = "dry",
    confidence_score: float = 0.9,
    prediction_status: str = "correct_prediction",
) -> SmartTireReport:
    """
    Convenience factory — construct a SmartTireReport from raw prediction values.

    Args:
        health_score:          AI model health output (0-10)
        tread_depth_mm:        Average tread depth in mm
        wear_label:            WearPatternClass value string (e.g. 'edge_wear')
        damage_label:          TireDamageClass value string
        road_condition_label:  RoadConditionClass value string
        weather_label:         WeatherConditionClass value string
        confidence_score:      Model confidence (0.0-1.0)
        prediction_status:     ContinuousLearningClass value string
    """
    health_cls  = classify_health(health_score)
    tread_cls   = classify_tread_depth(tread_depth_mm)
    wear_cls    = WEAR_LABEL_TO_CLASS.get(wear_label, WearPatternClass.EVEN_WEAR)
    damage_cls  = TireDamageClass(damage_label) if damage_label in TireDamageClass._value2member_map_ else TireDamageClass.NO_DAMAGE  # noqa: SLF001
    road_cls    = ROAD_LABEL_TO_CLASS.get(road_condition_label, RoadConditionClass.SMOOTH)
    weather_cls = WEATHER_LABEL_TO_CLASS.get(weather_label, WeatherConditionClass.DRY)
    conf_cls    = classify_confidence(confidence_score)
    learn_cls   = ContinuousLearningClass(prediction_status) if prediction_status in ContinuousLearningClass._value2member_map_ else ContinuousLearningClass.CORRECT_PREDICTION  # noqa: SLF001

    risk = risk_from_combined(health_cls, road_cls, weather_cls)
    adv  = advice_from_risk(risk)

    return SmartTireReport(
        tire_condition=health_cls,
        tread_depth_mm=tread_depth_mm,
        tread_class=tread_cls,
        wear_pattern=wear_cls,
        damage=damage_cls,
        road_condition=road_cls,
        weather=weather_cls,
        risk_level=risk,
        advice=adv,
        learning_status=learn_cls,
        confidence=conf_cls,
    )


# ── Module-level class count summary (useful for model config) ─────────────────
CLASS_SUMMARY: Dict[str, int] = {
    "tire_health_classes":    len(TireHealthClass),
    "tread_depth_classes":    len(TreadDepthClass),
    "wear_pattern_classes":   len(WearPatternClass),
    "tire_damage_classes":    len(TireDamageClass),
    "road_condition_classes": len(RoadConditionClass),
    "weather_classes":        len(WeatherConditionClass),
    "driving_risk_classes":   len(DrivingRiskClass),
    "driving_advice_classes": len(DrivingAdviceClass),
    "continuous_learning_classes": len(ContinuousLearningClass),
    "model_confidence_classes": len(ModelConfidenceClass),
    "total_unique_classes":   sum([
        len(TireHealthClass), len(TreadDepthClass), len(WearPatternClass),
        len(TireDamageClass), len(RoadConditionClass), len(WeatherConditionClass),
        len(DrivingRiskClass), len(DrivingAdviceClass),
        len(ContinuousLearningClass), len(ModelConfidenceClass),
    ]),
}
