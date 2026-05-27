import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.maps_service import MapsService
from app.services.ollama_service import OllamaService


@pytest.mark.asyncio
async def test_mock_route_context_contains_street_view_and_route_fields():
    service = MapsService()
    service.enabled = False
    service.rotator = None

    result = await service.get_route_road_context(28.6139, 77.2090, 28.7041, 77.1025)

    assert result["route_analysis_source"] == "mock"
    assert result["route_source_latitude"] == pytest.approx(28.6139)
    assert result["route_destination_longitude"] == pytest.approx(77.1025)
    assert result["street_view_available"] is False
    assert "street_view_visual_summary" in result
    assert result["route_distance_km"] > 0


def test_ollama_reasoning_normalizes_json_fields():
    service = OllamaService()
    result = service._normalize_reasoning(
        {
            "risk_level": "low",
            "driving_advice": "Keep speed steady and leave extra space on rough sections.",
            "replacement_recommended": False,
            "replacement_urgency": "monitor",
            "primary_cause": "Normal wear",
            "safety_score": 88,
        },
        {
            "tread_depths_mm": {"average": 7.0},
            "health_score": 8.0,
        },
    )

    assert result is not None
    assert result["risk_level"] == "LOW"
    assert result["replacement_urgency"] == "monitor"
    assert result["safety_score"] == 88
