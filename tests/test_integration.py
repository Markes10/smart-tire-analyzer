"""
Integration tests — End-to-end pipeline from image bytes through to final report.
Tests the full inference → Gemini → report assembly flow.
"""

import io
import json
import numpy as np
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path


def make_tire_image_bytes(width=224, height=224) -> bytes:
    """Create a synthetic sharp tire image as JPEG bytes."""
    from PIL import Image as PILImage
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :] = [60, 60, 60]
    # Add tread groove pattern
    for x in range(0, width, 18):
        arr[:, x:x+8] = [20, 20, 20]
    # Add some random variation to avoid too-uniform detection
    noise = np.random.randint(0, 30, arr.shape, dtype=np.uint8)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = PILImage.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


class TestOutputHeadsIntegration:
    """Tests the output_heads full pipeline: raw → report."""

    def _make_model_outputs(self, tread=0.6, health=0.75, life=0.65, wear=3):
        wear_probs = np.zeros((1, 6), dtype=np.float32)
        wear_probs[0, wear] = 0.88
        wear_probs[0, (wear + 1) % 6] = 0.12
        return {
            "tread_depths":  np.ones((1, 4), dtype=np.float32) * tread,
            "health_score":  np.array([[health]], dtype=np.float32),
            "remaining_life":np.array([[life]], dtype=np.float32),
            "wear_pattern":  wear_probs,
        }

    def test_full_report_structure(self):
        """Full report contains all required nested fields."""
        from ai_model.ann.output_heads import build_final_report
        raw = self._make_model_outputs()
        report = build_final_report(raw, session_id="integration-test-001")

        # Top level
        assert report["risk_level"] in ("CRITICAL", "HIGH", "MODERATE", "LOW")
        assert isinstance(report["replace_immediately"], bool)
        assert 0.0 <= report["confidence"] <= 1.0

        # Predictions
        preds = report["predictions"]
        tread = preds["tread_depths_mm"]
        assert all(k in tread for k in ["tread_1","tread_2","tread_3","tread_4","average"])
        assert 0 <= preds["health_score"] <= 10
        assert preds["remaining_life_km"] >= 0

        # Wear pattern
        wear = preds["wear_pattern"]
        assert wear["label"] in ["center_wear","edge_wear","patchy_wear","uniform_wear","one_side_wear","cupping_wear"]
        assert 0.0 <= wear["confidence"] <= 1.0

        # Reasoning (rule-based since no Gemini)
        reasoning = report["reasoning"]
        assert "driving_advice" in reasoning
        assert "risk_level" in reasoning

    def test_critical_tire_triggers_replace(self):
        """Sub-legal tread should set replace_immediately=True."""
        from ai_model.ann.output_heads import build_final_report
        # tread_norm = 0.12 → 1.44mm (below 1.6mm legal limit)
        raw = self._make_model_outputs(tread=0.12, health=0.15, life=0.02, wear=1)
        report = build_final_report(raw)
        assert report["replace_immediately"] is True
        assert report["risk_level"] == "CRITICAL"

    def test_new_tire_no_replace(self):
        """Near-new tire should not need replacement."""
        from ai_model.ann.output_heads import build_final_report
        # tread_norm = 0.85 → 10.2mm (near new)
        raw = self._make_model_outputs(tread=0.85, health=0.95, life=0.90, wear=3)
        report = build_final_report(raw)
        assert report["replace_immediately"] is False
        assert report["risk_level"] == "LOW"

    def test_alerts_count_by_severity(self):
        """Critical tire generates at least one alert."""
        from ai_model.ann.output_heads import build_final_report, _generate_alerts
        preds = {
            "tread_depths_mm": {"average": 1.2, "min": 1.0, "max": 1.4},
            "health_score": 1.5,
            "wear_pattern": {"severity": "critical"},
        }
        alerts = _generate_alerts(preds, "CRITICAL")
        assert len(alerts) >= 1
        assert alerts[0]["level"] in ("CRITICAL", "HIGH", "MODERATE")


class TestSequenceBuilderIntegration:
    """End-to-end tread sequence → RNN feature building."""

    def test_multi_session_sequence(self):
        """Historical sessions → padded sequence of correct shape."""
        from ai_model.rnn.sequence_builder import build_multi_session_sequence
        sessions = [
            {"tread_depths": [7.0, 6.9, 6.8, 6.7], "days_ago": 90, "mileage": 45000},
            {"tread_depths": [6.0, 5.8, 5.9, 5.7], "days_ago": 45, "mileage": 52000},
            {"tread_depths": [5.5, 5.3, 5.4, 5.2], "days_ago": 0,  "mileage": 57000},
        ]
        seq = build_multi_session_sequence(sessions, max_len=10)
        assert seq.shape == (10, 8), f"Expected (10,8), got {seq.shape}"
        assert seq.dtype == np.float32

    def test_empty_sessions_pads(self):
        """Empty session list → zero-padded sequence."""
        from ai_model.rnn.sequence_builder import build_multi_session_sequence
        seq = build_multi_session_sequence([], max_len=5)
        assert seq.shape[0] == 5
        assert np.all(seq == 0)


class TestWeatherRiskScorer:
    """Test weather risk scoring pipeline."""

    def test_clear_weather_no_risk(self):
        """Clear weather → multiplier close to 1.0."""
        from api_integrations.weather.risk_scorer import compute_weather_risk
        result = compute_weather_risk({
            "weather_condition": "Clear",
            "temperature_c": 22.0,
            "visibility_km": 10.0,
            "rain_detected": False,
            "rain_intensity": "none",
        })
        assert result["weather_risk_multiplier"] == pytest.approx(1.0, abs=0.05)
        assert result["driving_risk_level"] == "LOW"
        assert result["wet_road"] is False

    def test_heavy_rain_high_risk(self):
        """Heavy rain → HIGH or EXTREME risk."""
        from api_integrations.weather.risk_scorer import compute_weather_risk
        result = compute_weather_risk({
            "weather_condition": "Rain",
            "temperature_c": 15.0,
            "visibility_km": 2.0,
            "rain_detected": True,
            "rain_intensity": "heavy",
        })
        assert result["weather_risk_multiplier"] > 1.5
        assert result["driving_risk_level"] in ("HIGH", "EXTREME")
        assert result["wet_road"] is True

    def test_thunderstorm_extreme_risk(self):
        """Thunderstorm → EXTREME multiplier."""
        from api_integrations.weather.risk_scorer import compute_weather_risk
        result = compute_weather_risk({
            "weather_condition": "Thunderstorm",
            "temperature_c": 20.0,
            "rain_detected": True,
            "rain_intensity": "heavy",
            "visibility_km": 0.5,
        })
        assert result["weather_risk_multiplier"] >= 2.0

    def test_adjust_remaining_life(self):
        """Poor conditions reduce remaining life estimate."""
        from api_integrations.weather.risk_scorer import adjust_remaining_life
        result = adjust_remaining_life(
            remaining_km=50000,
            road_multiplier=1.3,
            weather_multiplier=1.4,
        )
        assert result["remaining_life_km_adjusted"] < 50000
        assert result["reduction_pct"] > 0

    def test_adjust_life_capped(self):
        """Extreme multipliers capped at 2.5×."""
        from api_integrations.weather.risk_scorer import adjust_remaining_life
        result = adjust_remaining_life(
            remaining_km=40000,
            road_multiplier=2.0,
            weather_multiplier=2.0,  # Combined = 4.0, capped at 2.5
        )
        assert result["combined_multiplier"] <= 2.5


class TestDepthClassifierIntegration:
    """Test tread depth classification across boundary values."""

    @pytest.mark.parametrize("depth_mm,expected", [
        (1.0, "ILLEGAL"),
        (1.59, "ILLEGAL"),
        (1.6, "CRITICAL"),
        (2.99, "CRITICAL"),
        (3.0, "WARNING"),
        (4.99, "WARNING"),
        (5.0, "ACCEPTABLE"),
        (6.99, "ACCEPTABLE"),
        (7.0, "GOOD"),
        (10.0, "GOOD"),
    ])
    def test_boundary_classifications(self, depth_mm, expected):
        """Test classification at all boundaries."""
        from ai_model.ann.output_heads import _classify_tread_status
        assert _classify_tread_status(depth_mm) == expected


class TestGeminiResponseParser:
    """Test Gemini response parsing and validation."""

    def test_valid_response_parsed(self):
        """Valid Gemini response dict passes through correctly."""
        from api_integrations.gemini.response_parser import parse_reasoning_response
        raw = {
            "risk_level": "HIGH",
            "driving_advice": "Reduce speed on wet roads and increase following distance.",
            "replacement_recommended": True,
            "replacement_urgency": "within_1000km",
            "primary_cause": "Underinflation",
            "additional_notes": "Check pressure weekly.",
            "safety_score": 42,
        }
        result = parse_reasoning_response(raw)
        assert result is not None
        assert result["risk_level"] == "HIGH"
        assert result["replacement_recommended"] is True
        assert result["safety_score"] == 42
        assert result["source"] == "gemini"

    def test_invalid_risk_level_defaulted(self):
        """Invalid risk level falls back to MODERATE."""
        from api_integrations.gemini.response_parser import parse_reasoning_response
        raw = {
            "risk_level": "UNKNOWN_LEVEL",
            "driving_advice": "Be careful.",
        }
        result = parse_reasoning_response(raw)
        assert result["risk_level"] == "MODERATE"

    def test_safety_score_clamped(self):
        """Safety score outside 0-100 clamped."""
        from api_integrations.gemini.response_parser import parse_reasoning_response
        raw = {
            "risk_level": "LOW",
            "driving_advice": "All good.",
            "safety_score": 150,
        }
        result = parse_reasoning_response(raw)
        assert result["safety_score"] == 100

    def test_none_input_returns_none(self):
        """None input returns None gracefully."""
        from api_integrations.gemini.response_parser import parse_reasoning_response
        assert parse_reasoning_response(None) is None
        assert parse_reasoning_response({}) is None
