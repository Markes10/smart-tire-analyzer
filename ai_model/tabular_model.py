"""
Shared PyTorch tabular model utilities for Smart Tire Analyzer.

This module mirrors the architecture used by ``scripts/prepare_and_train.py``
so the saved ``.pt`` weights can be loaded for runtime inference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - handled at runtime
    torch = None
    nn = Any  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ai_model" / "saved_models" / "smart_tire_tabular_best.pt"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "ai_model" / "saved_models" / "model_metadata.json"


class SmartTireTabular(nn.Module):
    """Tabular model trained on tread measurements."""

    def __init__(self, in_dim: int = 5) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(in_dim, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
        )
        self.condition_head = nn.Linear(128, 3)
        self.health_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        self.life_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):  # type: ignore[override]
        features = self.backbone(x)
        return (
            self.condition_head(features),
            self.health_head(features).squeeze(1),
            self.life_head(features).squeeze(1),
        )


def load_metadata(metadata_path: Path | str = DEFAULT_METADATA_PATH) -> dict[str, Any]:
    """Load tabular model metadata, falling back to sane defaults."""
    path = Path(metadata_path)
    defaults: dict[str, Any] = {
        "features": ["tread_1", "tread_2", "tread_3", "tread_4", "tread_average"],
        "feature_max": [12.0, 12.0, 12.0, 12.0, 12.0],
        "condition_classes": ["safe", "moderate", "replace"],
        "health_max": 10.0,
        "remaining_life_max_km": 80000.0,
        "model_type": "SmartTireTabular",
    }
    if not path.exists():
        return defaults

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    defaults.update(loaded)
    return defaults


def build_feature_vector(
    depths_mm: list[float],
    feature_max: list[float] | np.ndarray | None = None,
) -> np.ndarray:
    """Convert four tread depths into the normalized 5-feature vector used by training."""
    if len(depths_mm) != 4:
        raise ValueError("Exactly 4 tread depth measurements are required")

    clipped = np.clip(np.asarray(depths_mm, dtype=np.float32), 0.0, 12.0)
    if float(clipped[3]) <= 0.0:
        clipped[3] = float(np.mean(clipped[:3]))

    average = float(np.mean(clipped))
    feature_vector = np.asarray(
        [float(clipped[0]), float(clipped[1]), float(clipped[2]), float(clipped[3]), average],
        dtype=np.float32,
    )

    scale = np.asarray(feature_max or [12.0] * 5, dtype=np.float32)
    scale = np.where(scale <= 0.0, 12.0, scale)
    return feature_vector / scale


def load_trained_model(
    model_path: Path | str = DEFAULT_MODEL_PATH,
    device: str | None = None,
) -> tuple[Any, dict[str, Any], str] | None:
    """
    Load the trained PyTorch model bundle.

    Returns ``(model, metadata, device_name)`` or ``None`` if the runtime/model
    is unavailable.
    """
    if torch is None:
        return None

    weights_path = Path(model_path)
    if not weights_path.exists():
        return None

    metadata = load_metadata()
    device_name = device or ("cuda" if torch.cuda.is_available() else "cpu")
    runtime_device = torch.device(device_name)

    model = SmartTireTabular(in_dim=5).to(runtime_device)
    state_dict = torch.load(weights_path, map_location=runtime_device)
    model.load_state_dict(state_dict)
    model.eval()
    return model, metadata, device_name


def predict_from_depths(
    model: Any,
    metadata: dict[str, Any],
    device_name: str,
    depths_mm: list[float],
) -> dict[str, Any]:
    """Run inference from four tread depth measurements."""
    if torch is None:
        raise RuntimeError("PyTorch is not available")

    feature_vector = build_feature_vector(depths_mm, metadata.get("feature_max"))
    input_tensor = torch.from_numpy(feature_vector).unsqueeze(0).to(device_name)

    with torch.no_grad():
        condition_logits, health_norm, life_norm = model(input_tensor)
        condition_probs = torch.softmax(condition_logits, dim=1).cpu().numpy()[0]
        health_value = float(health_norm.cpu().numpy()[0]) * float(metadata.get("health_max", 10.0))
        remaining_km = float(life_norm.cpu().numpy()[0]) * float(
            metadata.get("remaining_life_max_km", 80000.0)
        )

    classes = metadata.get("condition_classes", ["safe", "moderate", "replace"])
    best_idx = int(np.argmax(condition_probs))

    return {
        "condition_label": classes[best_idx] if best_idx < len(classes) else "unknown",
        "condition_probs": condition_probs.tolist(),
        "condition_confidence": float(condition_probs[best_idx]),
        "health_score": float(np.clip(health_value, 0.0, metadata.get("health_max", 10.0))),
        "remaining_life_km": float(
            np.clip(remaining_km, 0.0, metadata.get("remaining_life_max_km", 80000.0))
        ),
        "features": feature_vector.tolist(),
    }
