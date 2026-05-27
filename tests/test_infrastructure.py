"""Tests for infrastructure modules: image optimizer, notifications, metrics, settings."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from utils.image_optimizer import optimize_image_bytes
from app.config import AppSettings
from app.main import create_app


def _jpeg_bytes(width: int = 320, height: int = 240) -> bytes:
    array = np.full((height, width, 3), 120, dtype=np.uint8)
    image = Image.fromarray(array)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


class TestImageOptimizer:
    def test_optimize_reduces_or_preserves_size(self):
        original = _jpeg_bytes()
        result = optimize_image_bytes(original, content_type="image/jpeg")
        assert result.optimized_bytes <= len(original)
        assert result.data
        assert result.content_type == "image/jpeg"

    def test_optimize_respects_max_dimension(self):
        original = _jpeg_bytes(width=4000, height=3000)
        result = optimize_image_bytes(original, content_type="image/jpeg", max_dimension=1024)
        with Image.open(io.BytesIO(result.data)) as image:
            assert max(image.size) <= 1024


class TestAppSettings:
    def test_validation_bounds(self):
        settings = AppSettings(
            CONFIDENCE_THRESHOLD=0.5,
            BLUR_THRESHOLD=80.0,
            API_PORT=8080,
            MAX_IMAGE_SIZE_MB=5,
        )
        assert settings.CONFIDENCE_THRESHOLD == 0.5
        assert settings.API_PORT == 8080

    def test_bool_parsing(self):
        settings = AppSettings(AUTH_ENABLED="true", IMAGE_OPTIMIZER_ENABLED="false")
        assert settings.AUTH_ENABLED is True
        assert settings.IMAGE_OPTIMIZER_ENABLED is False


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_payload(self):
        client = TestClient(create_app())
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "smart_tire_model_ready" in response.text
        assert "text/plain" in response.headers.get("content-type", "")


class TestRegistryEndpoint:
    def test_registry_404_when_missing(self):
        client = TestClient(create_app())
        with patch("app.routes.registry.REGISTRY_PATH") as mock_path:
            mock_path.exists.return_value = False
            response = client.get("/registry")
        assert response.status_code == 404

    def test_registry_returns_json(self, tmp_path):
        registry = tmp_path / "model_registry.json"
        payload = {"runtime_model": "hybrid_torch", "model_version": "test-v1", "models": {}}
        registry.write_text(json.dumps(payload), encoding="utf-8")

        client = TestClient(create_app())
        with patch("app.routes.registry.REGISTRY_PATH", registry):
            response = client.get("/registry")
        assert response.status_code == 200
        assert response.json()["model_version"] == "test-v1"


class TestNotificationService:
    def test_notifications_disabled_by_default(self):
        from app.services.notifications import NotificationService

        service = NotificationService()
        result = service.notify_model_promoted(model_version="demo", registry_path="/tmp/registry.json")
        assert result["sent"] is False

    @patch("app.services.notifications.request.urlopen")
    def test_webhook_dispatch(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 200
        settings = AppSettings(NOTIFICATIONS_ENABLED=True, NOTIFICATION_WEBHOOK_URL="https://example.com/hook")
        with patch("app.services.notifications.settings", settings):
            from app.services.notifications import NotificationService

            result = NotificationService().notify_model_promoted(
                model_version="demo",
                registry_path="/tmp/registry.json",
            )
        assert result["sent"] is True
        assert result["channels"]["webhook"]["ok"] is True
