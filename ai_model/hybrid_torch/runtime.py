"""Runtime helpers for the fresh PyTorch hybrid model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from ai_model.hybrid_torch.constants import HYBRID_MODEL_VERSION
from ai_model.hybrid_torch.calibration import (
    apply_tread_calibration_array,
    load_tread_calibrator,
)
from ai_model.hybrid_torch.dataset import bgr_image_to_tensor
from ai_model.hybrid_torch.model import build_model_from_checkpoint

DEFAULT_HYBRID_DIR = Path(__file__).resolve().parents[1] / "saved_models" / "hybrid_torch"
DEFAULT_CHECKPOINT = DEFAULT_HYBRID_DIR / "model_best.pt"
DEFAULT_METADATA = DEFAULT_HYBRID_DIR / "metadata.json"


def load_hybrid_model(
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT,
    metadata_path: str | Path = DEFAULT_METADATA,
    device: str | None = None,
) -> tuple[Any, dict[str, Any], str] | None:
    """Load the trained hybrid checkpoint, returning None when absent."""
    checkpoint_file = Path(checkpoint_path)
    if not checkpoint_file.exists():
        return None

    device_name = device or ("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_file, map_location=device_name)
    model = build_model_from_checkpoint(checkpoint, device=device_name)

    metadata_file = Path(metadata_path)
    metadata: dict[str, Any] = {}
    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata.setdefault("model_version", HYBRID_MODEL_VERSION)
    metadata.setdefault("checkpoint", str(checkpoint_file))
    calibration_path = metadata.get("calibration")
    if calibration_path:
        calibration_file = Path(calibration_path)
        if not calibration_file.is_absolute():
            calibration_file = Path(__file__).resolve().parents[2] / calibration_file
        calibrator = load_tread_calibrator(calibration_file)
        metadata["_tread_calibrator"] = calibrator
        setattr(model, "_tread_calibrator", calibrator)
    return model, metadata, device_name


def predict_hybrid(
    model: Any,
    device_name: str,
    image_bgr: np.ndarray,
    tread_sequence: np.ndarray,
) -> dict[str, np.ndarray]:
    """Run one hybrid inference and return normalized raw output arrays."""
    image_tensor = bgr_image_to_tensor(image_bgr).unsqueeze(0).to(device_name)
    sequence_tensor = torch.from_numpy(np.asarray(tread_sequence, dtype=np.float32)).unsqueeze(0).to(device_name)
    with torch.no_grad():
        outputs = model({"image": image_tensor, "tread_sequence": sequence_tensor})
        wear_probs = torch.softmax(outputs["wear_pattern"], dim=1)
        condition_probs = torch.softmax(outputs["condition"], dim=1)
    tread_depths = apply_tread_calibration_array(
        outputs["tread_depths"].detach().cpu().numpy(),
        getattr(model, "_tread_calibrator", None),
    )
    return {
        "tread_depths": tread_depths,
        "health_score": outputs["health_score"].detach().cpu().numpy(),
        "remaining_life": outputs["remaining_life"].detach().cpu().numpy(),
        "wear_pattern": wear_probs.detach().cpu().numpy(),
        "condition_probs": condition_probs.detach().cpu().numpy(),
        "source": np.asarray(["pytorch_hybrid"], dtype=object),
    }
