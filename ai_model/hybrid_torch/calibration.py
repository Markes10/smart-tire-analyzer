"""Tread-depth calibration helpers for hybrid model outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class IsotonicTreadCalibrator:
    """Serializable per-position isotonic mapping for normalized tread depths."""

    x_thresholds: list[list[float]]
    y_thresholds: list[list[float]]

    def transform(self, predictions: np.ndarray) -> np.ndarray:
        values = np.asarray(predictions, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != len(self.x_thresholds):
            return np.clip(values, 0.0, 1.0).astype(np.float32, copy=False)

        calibrated = np.empty_like(values, dtype=np.float32)
        for index, (x_values, y_values) in enumerate(zip(self.x_thresholds, self.y_thresholds)):
            if len(x_values) < 2 or len(y_values) < 2:
                calibrated[:, index] = values[:, index]
                continue
            calibrated[:, index] = np.interp(
                values[:, index],
                np.asarray(x_values, dtype=np.float32),
                np.asarray(y_values, dtype=np.float32),
                left=float(y_values[0]),
                right=float(y_values[-1]),
            )
        return np.clip(calibrated, 0.0, 1.0).astype(np.float32, copy=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "isotonic_per_tread_position",
            "x_thresholds": self.x_thresholds,
            "y_thresholds": self.y_thresholds,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IsotonicTreadCalibrator":
        return cls(
            x_thresholds=[[float(value) for value in row] for row in payload.get("x_thresholds", [])],
            y_thresholds=[[float(value) for value in row] for row in payload.get("y_thresholds", [])],
        )


def fit_isotonic_tread_calibrator(
    predictions: np.ndarray,
    targets: np.ndarray,
) -> IsotonicTreadCalibrator | None:
    """Fit one monotonic calibrator per tread position."""
    try:
        from sklearn.isotonic import IsotonicRegression
    except Exception:
        return None

    pred = np.clip(np.asarray(predictions, dtype=np.float32), 0.0, 1.0)
    target = np.clip(np.asarray(targets, dtype=np.float32), 0.0, 1.0)
    if pred.ndim != 2 or target.shape != pred.shape or pred.shape[0] < 8:
        return None

    x_thresholds: list[list[float]] = []
    y_thresholds: list[list[float]] = []
    for index in range(pred.shape[1]):
        model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        model.fit(pred[:, index], target[:, index])
        x_thresholds.append([float(value) for value in model.X_thresholds_.tolist()])
        y_thresholds.append([float(value) for value in model.y_thresholds_.tolist()])

    return IsotonicTreadCalibrator(x_thresholds=x_thresholds, y_thresholds=y_thresholds)


def save_tread_calibrator(calibrator: IsotonicTreadCalibrator | None, path: Path) -> str | None:
    if calibrator is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(calibrator.to_dict(), indent=2), encoding="utf-8")
    return str(path)


def load_tread_calibrator(path: str | Path) -> IsotonicTreadCalibrator | None:
    calibrator_path = Path(path)
    if not calibrator_path.exists():
        return None
    try:
        payload = json.loads(calibrator_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("type") != "isotonic_per_tread_position":
        return None
    return IsotonicTreadCalibrator.from_dict(payload)


def apply_tread_calibration_array(
    predictions: np.ndarray,
    calibrator: IsotonicTreadCalibrator | None,
) -> np.ndarray:
    if calibrator is None:
        return np.clip(np.asarray(predictions, dtype=np.float32), 0.0, 1.0)
    return calibrator.transform(predictions)
