from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.services import continuous_learning_service as service


def test_save_feedback_correction_returns_trainable_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    image_path = tmp_path / "front_view" / "sample.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")

    monkeypatch.setattr(service, "CONTINUOUS_ROOT", tmp_path)
    monkeypatch.setattr(service, "CORRECTIONS_DIR", tmp_path / "corrections")
    monkeypatch.setattr(service, "LABELS_CSV", tmp_path / "labels.csv")

    result = service.save_feedback_correction(
        session_id="session-1",
        analysis_report={
            "metadata": {"continuous_learning_image_path": str(image_path)},
            "predictions": {},
        },
        feedback_record={
            "feedback_type": "wrong",
            "user_corrected_tread_mm": 5.25,
            "user_corrected_tread_depths_mm": {
                "tread_1": 5.1,
                "tread_2": 5.2,
                "tread_3": 5.3,
                "tread_4": 5.4,
            },
            "comment": "manual gauge reading",
        },
    )

    assert result["continuous_learning_image_path"] == str(image_path)
    assert (tmp_path / "labels.csv").read_text(encoding="utf-8").count("session-1") == 1
    assert Path(result["continuous_learning_correction_path"]).is_file()


def test_save_feedback_correction_rejects_missing_analysis_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(service, "CONTINUOUS_ROOT", tmp_path)
    monkeypatch.setattr(service, "CORRECTIONS_DIR", tmp_path / "corrections")
    monkeypatch.setattr(service, "LABELS_CSV", tmp_path / "labels.csv")

    with pytest.raises(ValueError, match="no saved analysis image"):
        service.save_feedback_correction(
            session_id="session-2",
            analysis_report={},
            feedback_record={
                "feedback_type": "wrong",
                "user_corrected_tread_mm": 4.0,
            },
        )

    assert not (tmp_path / "labels.csv").exists()
