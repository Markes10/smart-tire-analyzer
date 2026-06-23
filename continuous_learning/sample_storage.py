"""
Continuous-learning sample storage.

The analysis endpoint stores accepted front-view images here, and feedback
stores corrected labels against those saved samples. The full retraining job can
then consume dataset/continuous_learning without relying on browser session data.

Moved here from backend/app/services/continuous_learning_service.py to consolidate
all continuous-learning modules under one package.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTINUOUS_ROOT = PROJECT_ROOT / "dataset" / "continuous_learning"
FRONT_VIEW_DIR = CONTINUOUS_ROOT / "front_view"
PREDICTIONS_DIR = CONTINUOUS_ROOT / "predictions"
CORRECTIONS_DIR = CONTINUOUS_ROOT / "corrections"
LABELS_CSV = CONTINUOUS_ROOT / "labels.csv"

IMAGE_EXTENSIONS_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

LABEL_COLUMNS = [
    "session_id",
    "image_path",
    "tread_1",
    "tread_2",
    "tread_3",
    "tread_4",
    "tread_average",
    "wear_pattern",
    "health_score",
    "feedback_type",
    "comment",
    "timestamp",
]


def _safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return cleaned[:120] or "sample"


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _resolve_project_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def save_analysis_sample(
    *,
    session_id: str,
    image_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    report: dict[str, Any],
) -> dict[str, str]:
    FRONT_VIEW_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    source_suffix = Path(filename or "").suffix.lower()
    suffix = source_suffix if source_suffix in {".jpg", ".jpeg", ".png", ".webp"} else IMAGE_EXTENSIONS_BY_TYPE.get(content_type or "", ".jpg")
    image_path = FRONT_VIEW_DIR / f"{_safe_stem(session_id)}{suffix}"
    image_path.write_bytes(image_bytes)

    prediction_path = PREDICTIONS_DIR / f"{_safe_stem(session_id)}.json"
    prediction_path.write_text(
      json.dumps(
        {
          "session_id": session_id,
          "source_filename": filename,
          "content_type": content_type,
          "image_path": _relative(image_path),
          "saved_at": datetime.now(timezone.utc).isoformat(),
          "predictions": report.get("predictions", {}),
          "risk_level": report.get("risk_level"),
          "confidence": report.get("confidence"),
          "model_version": report.get("model_version"),
        },
        indent=2,
        default=str,
      ),
      encoding="utf-8",
    )

    return {
        "continuous_learning_image_path": _relative(image_path),
        "continuous_learning_prediction_path": _relative(prediction_path),
    }


def save_feedback_correction(
    *,
    session_id: str,
    analysis_report: dict[str, Any] | None,
    feedback_record: dict[str, Any],
) -> dict[str, str]:
    CONTINUOUS_ROOT.mkdir(parents=True, exist_ok=True)
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    metadata = (analysis_report or {}).get("metadata", {}) if isinstance(analysis_report, dict) else {}
    if not metadata:
        original_prediction = feedback_record.get("original_prediction")
        if isinstance(original_prediction, dict):
            metadata = original_prediction.get("metadata", {}) or {}
    image_path = metadata.get("continuous_learning_image_path", "")
    corrected_depths = feedback_record.get("user_corrected_tread_depths_mm") or {}
    average = feedback_record.get("user_corrected_tread_mm")
    if average is None and corrected_depths:
        numeric_depths = [
            float(value)
            for value in corrected_depths.values()
            if isinstance(value, (int, float))
        ]
        if numeric_depths:
            average = sum(numeric_depths) / len(numeric_depths)

    resolved_image_path = _resolve_project_path(image_path)
    if resolved_image_path is None or not resolved_image_path.is_file():
        raise ValueError(
            "Feedback cannot be added to the training queue because no saved analysis image was found."
        )

    if average is None and not corrected_depths:
        raise ValueError("Feedback cannot be trained without corrected tread depth labels.")

    row = {
        "session_id": session_id,
        "image_path": image_path,
        "tread_1": corrected_depths.get("tread_1", average),
        "tread_2": corrected_depths.get("tread_2", average),
        "tread_3": corrected_depths.get("tread_3", average),
        "tread_4": corrected_depths.get("tread_4", average),
        "tread_average": average,
        "wear_pattern": feedback_record.get("user_corrected_wear_pattern"),
        "health_score": feedback_record.get("user_corrected_health_score"),
        "feedback_type": feedback_record.get("feedback_type"),
        "comment": feedback_record.get("comment"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    file_exists = LABELS_CSV.exists()
    with LABELS_CSV.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    correction_path = CORRECTIONS_DIR / f"{_safe_stem(session_id)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    correction_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "image_path": image_path,
                "feedback": feedback_record,
                "analysis_summary": {
                    "predictions": (analysis_report or {}).get("predictions", {}),
                    "risk_level": (analysis_report or {}).get("risk_level"),
                    "confidence": (analysis_report or {}).get("confidence"),
                },
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return {
        "continuous_learning_image_path": image_path,
        "continuous_learning_labels_path": _relative(LABELS_CSV),
        "continuous_learning_correction_path": _relative(correction_path),
    }
