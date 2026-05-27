import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from api_integrations.gemini import gemini_client


def test_gemini_client_uses_gemini_api_keys_env(monkeypatch):
    from app.services import api_key_rotator

    monkeypatch.setattr(gemini_client, "_get_settings", lambda: None)
    monkeypatch.setattr(api_key_rotator, "_gemini_rotator", None)
    monkeypatch.setenv("GEMINI_API_KEYS", "key-one,key-two")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = gemini_client.GeminiClient()

    assert client.is_available()
    assert client.api_key == "key-one"
    assert client.rotator is not None
    assert client.rotator.available_keys == ["key-one", "key-two"]


def test_parse_json_object_handles_nested_fenced_json():
    parsed = gemini_client._parse_json_object(
        """```json
{"brand":"MRF","tire_size":{"raw":"185/65 R15","full_formatted":"185/65 R15"}}
```"""
    )

    assert parsed is not None
    assert parsed["tire_size"]["raw"] == "185/65 R15"


@pytest.mark.asyncio
async def test_sidewall_analyzer_sends_uploaded_image_to_gemini(monkeypatch):
    from api_integrations.gemini.sidewall_analyzer import SidewallAnalyzer

    calls = {}

    class FakeGeminiClient:
        def is_available(self):
            return True

        async def generate_with_image(self, **kwargs):
            calls.update(kwargs)
            return {
                "brand": "mrf",
                "tire_model": "ZVTV",
                "tire_size": {
                    "raw": "185/65 R15",
                    "width_mm": 185,
                    "aspect_ratio": 65,
                    "rim_diameter_inches": 15,
                    "full_formatted": "185/65 R15",
                },
                "special_markings": ["TUBELESS"],
                "extraction_confidence": "HIGH",
            }

    fake_client = FakeGeminiClient()
    monkeypatch.setattr(gemini_client, "get_gemini_client", lambda: fake_client)

    result = await SidewallAnalyzer().extract(b"sidewall-image-bytes", mime_type="image/png")

    assert calls["image_bytes"] == b"sidewall-image-bytes"
    assert calls["mime_type"] == "image/png"
    assert calls["max_tokens"] == 4096
    assert "sidewall" in calls["prompt"].lower()
    assert result["source"] == "gemini_vision"
    assert result["brand"] == "MRF"
