from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _image_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), color=(80, 80, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_resolve_hybrid_artifacts_prefers_best_and_metadata_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.services import inference_service as service_module

    model_dir = tmp_path / "hybrid_torch"
    model_dir.mkdir()
    best = model_dir / "model_best.pt"
    last = model_dir / "model_last.pt"
    metadata = model_dir / "metadata.json"
    best.write_bytes(b"best")
    last.write_bytes(b"last")
    metadata.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(service_module, "HYBRID_ACCEPTED_MODEL_PATH", best)
    monkeypatch.setattr(service_module, "HYBRID_LAST_MODEL_PATH", last)
    monkeypatch.setattr(service_module, "HYBRID_METADATA_PATH", metadata)

    artifacts = service_module.InferenceService()._resolve_hybrid_artifacts()

    assert artifacts == (best, metadata, "accepted")


def test_resolve_hybrid_artifacts_falls_back_to_last_with_metadata_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import inference_service as service_module

    model_dir = tmp_path / "hybrid_torch"
    model_dir.mkdir()
    best = model_dir / "model_best.pt"
    last = model_dir / "model_last.pt"
    metadata = model_dir / "metadata.json"
    eval_report = model_dir / "model_last_eval_test.json"
    last.write_bytes(b"last")
    metadata.write_text("{}", encoding="utf-8")
    eval_report.write_text('{"should_not_be_used_as_metadata": true}', encoding="utf-8")

    monkeypatch.setattr(service_module, "HYBRID_ACCEPTED_MODEL_PATH", best)
    monkeypatch.setattr(service_module, "HYBRID_LAST_MODEL_PATH", last)
    monkeypatch.setattr(service_module, "HYBRID_METADATA_PATH", metadata)

    artifacts = service_module.InferenceService()._resolve_hybrid_artifacts()

    assert artifacts == (last, metadata, "unaccepted_last")


def test_depth_wear_pattern_detects_side_wall_and_preserves_existing_patterns():
    from app.services.inference_service import _infer_wear_pattern_from_depths

    assert _infer_wear_pattern_from_depths([2.0, 2.4, 2.6, 4.0]) == "side_wall_wear"
    assert _infer_wear_pattern_from_depths([5.0, 5.1, 5.0, 5.2]) == "uniform_wear"
    assert _infer_wear_pattern_from_depths([5.0, 3.0, 3.0, 5.0]) == "center_wear"
    assert _infer_wear_pattern_from_depths([3.0, 5.0, 5.0, 3.0]) == "edge_wear"
    assert _infer_wear_pattern_from_depths([5.0, 4.8, 4.7, 2.8]) == "one_side_wear"


def test_depth_wear_override_marks_side_wall_without_changing_model_tensor_shape():
    from app.services.inference_service import InferenceService

    prediction = {
        "wear_pattern": {
            "class_id": 3,
            "label": "uniform_wear",
            "confidence": 0.7,
            "probabilities": {"uniform_wear": 0.7},
        }
    }

    InferenceService()._apply_depth_wear_override(prediction, [2.0, 2.4, 2.6, 4.0])

    assert prediction["wear_pattern"]["label"] == "side_wall_wear"
    assert prediction["wear_pattern"]["class_id"] == -1
    assert prediction["model_wear_pattern_before_depth_override"] == "uniform_wear"
    assert prediction["side_wall_wear_rule"]["outer_minus_inner_mm"] == pytest.approx(2.0)


def test_sanity_check_passes_with_report_shaped_prediction(monkeypatch: pytest.MonkeyPatch):
    from app.services.inference_service import InferenceService

    service = InferenceService()
    service._hybrid_model = object()

    def fake_hybrid_infer(_image, _sequence):
        return {"wear_pattern": {"label": "uniform_wear", "confidence": 0.8}, "confidence": 0.8}

    monkeypatch.setattr(service, "_hybrid_infer", fake_hybrid_infer)

    service._sanity_check()


def test_sanity_check_raises_for_invalid_prediction(monkeypatch: pytest.MonkeyPatch):
    from app.services.inference_service import InferenceService

    service = InferenceService()
    service._hybrid_model = object()

    def fake_hybrid_infer(_image, _sequence):
        return {"wear_pattern": {"label": 123}, "confidence": 1.2}

    monkeypatch.setattr(service, "_hybrid_infer", fake_hybrid_infer)

    with pytest.raises(RuntimeError, match="Inference sanity check failed"):
        service._sanity_check()


def _app_with_fake_inference(monkeypatch: pytest.MonkeyPatch):
    from app.routes import inference as inference_route

    class FakeInference:
        def __init__(self) -> None:
            self.context_data = None

        async def predict(self, image_bytes, session_id, context_data=None):
            self.context_data = context_data
            return {
                "tread_depths_mm": {
                    "tread_1": 6.5,
                    "tread_2": 6.3,
                    "tread_3": 6.4,
                    "tread_4": 6.2,
                    "average": 6.35,
                    "min": 6.2,
                    "max": 6.5,
                },
                "health_score": 8.0,
                "remaining_life_km": 55000.0,
                "wear_pattern": {
                    "class_id": 3,
                    "label": "uniform_wear",
                    "cause": "Normal wear",
                    "severity": "low",
                    "confidence": 0.85,
                    "probabilities": {"uniform_wear": 0.85},
                },
                "confidence": 0.85,
                "source": "test",
                "depth_derived_wear_pattern": "uniform_wear",
            }

    class FakeReasoner:
        async def reason(self, predictions, context):
            return {
                "source": "test",
                "risk_level": "LOW",
                "driving_advice": "Continue monitoring.",
                "replacement_recommended": False,
            }

    class FakeEnterpriseAI:
        def build_analysis_extensions(self, *args, **kwargs):
            return {}

    fake_inference = FakeInference()
    app = FastAPI()
    app.include_router(inference_route.router, prefix="/analyze")
    app.dependency_overrides[inference_route.get_inference_service] = lambda: fake_inference

    monkeypatch.setattr(inference_route, "OllamaService", lambda: FakeReasoner())
    monkeypatch.setattr(inference_route, "EnterpriseAIService", lambda: FakeEnterpriseAI())
    monkeypatch.setattr(inference_route, "save_analysis_sample", lambda **kwargs: {})
    monkeypatch.setattr(inference_route, "save_analysis_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(inference_route, "record_analyze_request", lambda *args, **kwargs: None)
    return app, fake_inference


def test_analyze_accepts_multipart_context_json(monkeypatch: pytest.MonkeyPatch):
    app, fake_inference = _app_with_fake_inference(monkeypatch)

    response = TestClient(app).post(
        "/analyze",
        files={"image": ("tire.jpg", _image_bytes(), "image/jpeg")},
        data={"context": '{"tire_pressure_psi":32,"temperature_c":40}'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["confidence"] == 0.85
    assert payload["predictions"]["wear_pattern"]["label"] == "uniform_wear"
    assert payload["metadata"]["model_diagnostics"]["depth_derived_wear_pattern"] == "uniform_wear"
    assert fake_inference.context_data["tire_pressure_psi"] == 32.0
    assert fake_inference.context_data["temperature_c"] == 40.0


def test_analyze_rejects_invalid_context_json(monkeypatch: pytest.MonkeyPatch):
    app, _fake_inference = _app_with_fake_inference(monkeypatch)

    response = TestClient(app).post(
        "/analyze",
        files={"image": ("tire.jpg", _image_bytes(), "image/jpeg")},
        data={"context": "{not-json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "context must be valid JSON"
