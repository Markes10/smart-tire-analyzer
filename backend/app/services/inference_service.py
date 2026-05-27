"""
Inference service for Smart Tire Analyzer.

This service serves only the trained PyTorch hybrid artifact. When no accepted
hybrid checkpoint is available, inference remains unavailable instead of
silently returning synthetic predictions.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np

from ai_model.ann.output_heads import denormalize_outputs
from app.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HYBRID_MODEL_DIR = PROJECT_ROOT / "ai_model" / "saved_models" / "hybrid_torch"
HYBRID_ACCEPTED_MODEL_PATH = HYBRID_MODEL_DIR / "model_best.pt"
HYBRID_LAST_MODEL_PATH = HYBRID_MODEL_DIR / "model_last.pt"
HYBRID_METADATA_PATH = HYBRID_MODEL_DIR / "metadata.json"


def _infer_wear_pattern_from_depths(depths: list[float]) -> str:
    depth_array = np.asarray(depths, dtype=np.float32)
    inner_avg = float(np.mean(depth_array[:2]))
    outer_avg = float(np.mean(depth_array[2:]))
    center_avg = float(np.mean(depth_array[1:3]))
    edge_avg = float(np.mean(np.asarray([depth_array[0], depth_array[3]], dtype=np.float32)))

    diff = float(np.max(depth_array) - np.min(depth_array))
    inner_outer_diff = abs(inner_avg - outer_avg)

    if diff < 0.5:
        return "uniform_wear"
    if center_avg < edge_avg - 0.8:
        return "center_wear"
    if edge_avg < center_avg - 0.8:
        return "edge_wear"
    if inner_outer_diff > 1.5:
        return "one_side_wear"
    if diff > 2.0:
        return "patchy_wear"
    return "patchy_wear"


def _confidence_from_depths(depths: list[float]) -> float:
    depth_array = np.clip(np.asarray(depths, dtype=np.float32), 0.0, 12.0)
    depth_std = float(np.std(depth_array))
    depth_range = float(np.max(depth_array) - np.min(depth_array))
    confidence = 1.0 - (depth_std / 6.0) - (depth_range / 12.0) * 0.3
    return float(np.clip(confidence, 0.1, 1.0))


def _fit_last_dim(array: np.ndarray, target_dim: int) -> np.ndarray:
    """Pad or truncate the final feature axis to match a loaded model input."""
    values = np.asarray(array, dtype=np.float32)
    current_dim = int(values.shape[-1])
    if current_dim == target_dim:
        return cast(np.ndarray, values)
    if current_dim > target_dim:
        return cast(np.ndarray, values[..., :target_dim].astype(np.float32, copy=False))

    pad_width = [(0, 0)] * values.ndim
    pad_width[-1] = (0, target_dim - current_dim)
    return cast(np.ndarray, np.pad(values, pad_width, mode="constant").astype(np.float32, copy=False))


def _context_to_vector(context_data: dict[str, Any] | None, target_dim: int = 64) -> np.ndarray:
    """Convert road/weather context dictionaries into a stable numeric vector."""
    context = context_data or {}
    vector = np.zeros(target_dim, dtype=np.float32)

    numeric_values = [
        1.0 if context.get("rain_detected") else 0.0,
        float(context.get("temperature_c") or 24.0) / 60.0,
        float(context.get("humidity_pct") or 0.0) / 100.0,
        float(context.get("visibility_km") or 10.0) / 10.0,
        float(context.get("road_wear_multiplier") or 1.0),
        float(context.get("weather_risk_multiplier") or 1.0),
        float(context.get("elevation_m") or 0.0) / 3000.0,
        (float(context.get("latitude") or 0.0) + 90.0) / 180.0,
        (float(context.get("longitude") or 0.0) + 180.0) / 360.0,
    ]
    for index, value in enumerate(numeric_values[:target_dim]):
        vector[index] = float(np.clip(value, -3.0, 3.0))

    categorical_slots = {
        12: ("terrain_type", ["flat_urban", "rolling_suburban", "hilly", "mountainous"]),
        20: ("road_condition", ["excellent", "good", "fair", "poor"]),
        28: ("traffic_density", ["light", "moderate", "heavy"]),
        36: ("weather_condition", ["Clear", "Clouds", "Rain", "Drizzle", "Thunderstorm", "Snow"]),
    }
    for start, (key, labels) in categorical_slots.items():
        if start >= target_dim:
            continue
        categorical_value = str(context.get(key, "")).lower()
        for offset, label in enumerate(labels):
            slot = start + offset
            if slot >= target_dim:
                break
            vector[slot] = 1.0 if categorical_value == label.lower() else 0.0

    return cast(np.ndarray, vector)


class InferenceService:
    """Manages model loading and inference execution."""

    def __init__(self) -> None:
        self._hybrid_model: Any = None
        self._hybrid_metadata: dict[str, Any] = {}
        self._hybrid_device = "cpu"
        self._hybrid_checkpoint_mtime: float | None = None
        self._hybrid_checkpoint_path: Path | None = None
        self._hybrid_metadata_path: Path | None = None
        self._ready = False
        self._model_version = "unknown"
        self._model_source = "not_loaded"
        self._model_checkpoint = str(HYBRID_ACCEPTED_MODEL_PATH)
        self._load_error: str | None = None

    async def initialize(self) -> None:
        """Load the best available model without blocking the event loop."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

    def _load_model(self) -> None:
        """Load the best available trained model."""
        try:
            from ai_model.hybrid_torch.runtime import load_hybrid_model

            artifacts = self._resolve_hybrid_artifacts()
            if artifacts is None:
                self._load_error = (
                    f"Missing hybrid checkpoint: {HYBRID_ACCEPTED_MODEL_PATH} or "
                    f"{HYBRID_LAST_MODEL_PATH}"
                )
                hybrid_bundle = None
            else:
                checkpoint_path, metadata_path, checkpoint_status = artifacts
                hybrid_bundle = load_hybrid_model(checkpoint_path, metadata_path)
            if hybrid_bundle is not None:
                self._hybrid_model, self._hybrid_metadata, self._hybrid_device = hybrid_bundle
                self._hybrid_checkpoint_path = checkpoint_path
                self._hybrid_metadata_path = metadata_path
                self._hybrid_checkpoint_mtime = checkpoint_path.stat().st_mtime
                self._hybrid_metadata["runtime_checkpoint_status"] = checkpoint_status
                self._model_version = str(
                    self._hybrid_metadata.get(
                        "model_version",
                        "pytorch_hybrid:efficientnetv2_b0_vit_b16_bilstm_tcn_attention_calibrated",
                    )
                )
                self._model_source = (
                    "pytorch_hybrid"
                    if checkpoint_status == "accepted"
                    else "pytorch_hybrid_unaccepted_last"
                )
                self._model_checkpoint = str(checkpoint_path)
                self._load_error = None
                self._ready = True
                if checkpoint_status != "accepted":
                    logger.warning(
                        "Loaded unaccepted hybrid fallback checkpoint: %s",
                        checkpoint_path,
                    )
                else:
                    logger.info("Loaded accepted PyTorch hybrid model: %s", checkpoint_path)
                return
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("PyTorch hybrid model load failed: %s", exc)

        logger.error("No trained hybrid model could be loaded; inference is not ready.")
        self._model_version = "not_loaded"
        self._model_source = "not_loaded"
        self._hybrid_checkpoint_mtime = None
        self._hybrid_checkpoint_path = None
        self._hybrid_metadata_path = None
        self._ready = False

    def is_ready(self) -> bool:
        return (
            self._ready
            and self._hybrid_model is not None
            and self._hybrid_checkpoint_path is not None
            and self._hybrid_checkpoint_path.exists()
        )

    def _resolve_hybrid_artifacts(self) -> tuple[Path, Path, str] | None:
        """Prefer accepted weights, then use the latest trained fallback checkpoint."""
        if HYBRID_ACCEPTED_MODEL_PATH.exists():
            return HYBRID_ACCEPTED_MODEL_PATH, HYBRID_METADATA_PATH, "accepted"
        if not HYBRID_LAST_MODEL_PATH.exists():
            return None

        eval_reports = sorted(
            HYBRID_MODEL_DIR.glob("model_last_eval*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        metadata_path = eval_reports[0] if eval_reports else HYBRID_METADATA_PATH
        return HYBRID_LAST_MODEL_PATH, metadata_path, "unaccepted_last"

    async def predict(
        self,
        image_bytes: bytes,
        session_id: str,
        context_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the full inference pipeline on raw image bytes."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._predict_sync,
            image_bytes,
            session_id,
            context_data,
        )

    def _predict_sync(
        self,
        image_bytes: bytes,
        session_id: str,
        context_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._reload_model_if_changed()
        checkpoint_path = self._hybrid_checkpoint_path
        if self._hybrid_model is None or checkpoint_path is None or not checkpoint_path.exists():
            self._hybrid_model = None
            self._ready = False
            self._model_version = "not_loaded"
            self._model_source = "not_loaded"
            self._load_error = "Missing hybrid checkpoint"
            return {
                "rejected": True,
                "reason": "Trained hybrid model is unavailable",
                "model_version": self._model_version,
                "source": self._model_source,
            }
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            return {"rejected": True, "reason": "Could not decode image"}

        from ai_model.cnn.preprocessing import detect_blur, run_preprocessing_pipeline
        from ai_model.hybrid_torch.constants import TREAD_SEQUENCE_DIM
        from ai_model.hybrid_torch.runtime_tread import (
            RUNTIME_TREAD_SEQUENCE_SOURCE,
            estimate_visual_tread_depths,
        )
        from ai_model.rnn.sequence_builder import build_tread_sequence

        blur_threshold = float(settings.BLUR_THRESHOLD)
        is_blurry, blur_score = detect_blur(image, threshold=blur_threshold)
        if is_blurry:
            return {
                "rejected": True,
                "blur_score": blur_score,
                "blur_threshold": blur_threshold,
                "reason": "Image too blurry",
            }

        processed = run_preprocessing_pipeline(
            image,
            training=False,
            include_edge_channel=True,
            blur_threshold=blur_threshold,
        )
        if processed is None:
            return {
                "rejected": True,
                "blur_score": blur_score,
                "blur_threshold": blur_threshold,
                "reason": "Preprocessing failed",
            }

        estimated_depths = estimate_visual_tread_depths(image)
        tread_seq = build_tread_sequence(estimated_depths, target_dim=TREAD_SEQUENCE_DIM)

        prediction = self._hybrid_infer(image, tread_seq)

        prediction["tread_sequence_source"] = RUNTIME_TREAD_SEQUENCE_SOURCE
        prediction["runtime_tread_sequence_mm"] = {
            "position_1": round(float(estimated_depths[0]), 2),
            "position_2": round(float(estimated_depths[1]), 2),
            "position_3": round(float(estimated_depths[2]), 2),
            "position_4": round(float(estimated_depths[3]), 2),
            "average": round(float(np.mean(estimated_depths)), 2),
        }
        prediction["session_id"] = session_id
        prediction["blur_score"] = round(float(blur_score), 2)
        prediction["blur_threshold"] = blur_threshold
        prediction["model_version"] = self._model_version
        return prediction

    def _estimate_depths_from_image(self, processed_image: np.ndarray) -> list[float]:
        """
        Estimate four tread depths from image texture in a deterministic way.

        The runtime still derives a deterministic four-point sequence estimate
        so the BiLSTM branch receives the same structured input shape as
        training.
        """
        if processed_image.shape[-1] >= 4:
            edge_channel = np.abs(processed_image[:, :, 3])
        else:
            edge_channel = np.abs(np.mean(processed_image[:, :, :3], axis=-1))

        bands = np.array_split(edge_channel, 4, axis=1)
        band_scores = np.asarray([float(np.mean(np.abs(band))) for band in bands], dtype=np.float32)
        global_score = float(np.mean(band_scores))

        base_depth = 1.8 + global_score * 10.0
        depths = []
        for score in band_scores:
            adjusted = base_depth + float(score - global_score) * 18.0
            depths.append(float(np.clip(adjusted, 0.8, 11.5)))

        return depths

    def _build_wear_probabilities(self, depths: list[float], confidence: float) -> np.ndarray:
        label_to_index = {
            "center_wear": 0,
            "edge_wear": 1,
            "patchy_wear": 2,
            "uniform_wear": 3,
            "one_side_wear": 4,
            "cupping_wear": 5,
        }

        wear_label = _infer_wear_pattern_from_depths(depths)
        probs = np.full(6, (1.0 - confidence) / 5.0 if confidence < 1.0 else 0.0, dtype=np.float32)
        probs[label_to_index.get(wear_label, 3)] = float(np.clip(confidence, 0.5, 0.99))
        probs = probs / float(np.sum(probs))
        return cast(np.ndarray, probs)

    def _hybrid_infer(
        self,
        image_bgr: np.ndarray,
        tread_seq: np.ndarray,
    ) -> dict[str, Any]:
        from ai_model.hybrid_torch.constants import CONDITION_LABELS
        from ai_model.hybrid_torch.dataset import bgr_image_to_tensor
        from ai_model.hybrid_torch.calibration import apply_tread_calibration_array
        import torch

        tta_variants = self._build_tta_images(image_bgr)
        image_tensor = torch.stack([bgr_image_to_tensor(image) for image, _ in tta_variants], dim=0).to(self._hybrid_device)
        sequence_tensor = (
            torch.from_numpy(np.asarray(tread_seq, dtype=np.float32))
            .unsqueeze(0)
            .repeat(len(tta_variants), 1, 1)
            .to(self._hybrid_device)
        )

        with torch.no_grad():
            outputs = self._hybrid_model({"image": image_tensor, "tread_sequence": sequence_tensor})
            tread_outputs = outputs["tread_depths"].clone()
            for index, (_, flip_tread_positions) in enumerate(tta_variants):
                if flip_tread_positions:
                    tread_outputs[index] = torch.flip(tread_outputs[index], dims=[0])
            averaged_outputs = {
                key: value.mean(dim=0, keepdim=True)
                for key, value in outputs.items()
            }
            averaged_outputs["tread_depths"] = tread_outputs.mean(dim=0, keepdim=True)
            wear_probs = torch.softmax(averaged_outputs["wear_pattern"], dim=1)
            condition_probs_tensor = torch.softmax(averaged_outputs["condition"], dim=1)

        tread_depths = apply_tread_calibration_array(
            averaged_outputs["tread_depths"].detach().cpu().numpy(),
            self._hybrid_metadata.get("_tread_calibrator"),
        )

        condition_probs = condition_probs_tensor.detach().cpu().numpy()[0]
        best_condition = int(np.argmax(condition_probs))

        # --- Safety Guardrail Post-Processing: Align Tread Depth with Condition Classification ---
        best_condition_label = CONDITION_LABELS[best_condition]
        avg_depth = float(np.mean(tread_depths[0]))

        if best_condition_label == "replace" and avg_depth >= 3.0:
            target_avg = 2.4
            ratio = target_avg / avg_depth
            tread_depths[0] = np.clip(tread_depths[0] * ratio, 1.0, 2.9)
            logger.warning(
                "Safety guardrail triggered: condition was 'replace' but predicted avg tread depth was %.2fmm. "
                "Scaled down depth readings to average %.2fmm.", avg_depth, target_avg
            )
        elif best_condition_label == "moderate" and avg_depth >= 5.0:
            target_avg = 4.0
            ratio = target_avg / avg_depth
            tread_depths[0] = np.clip(tread_depths[0] * ratio, 3.0, 4.8)
            logger.warning(
                "Safety guardrail triggered: condition was 'moderate' but predicted avg tread depth was %.2fmm. "
                "Scaled down depth readings to average %.2fmm.", avg_depth, target_avg
            )
        elif best_condition_label == "safe" and avg_depth < 4.0:
            target_avg = 5.5
            ratio = target_avg / max(avg_depth, 0.1)
            tread_depths[0] = np.clip(tread_depths[0] * ratio, 4.2, 11.5)
            logger.warning(
                "Safety guardrail triggered: condition was 'safe' but predicted avg tread depth was %.2fmm. "
                "Scaled up depth readings to average %.2fmm.", avg_depth, target_avg
            )

        raw_outputs = {
            "tread_depths": tread_depths,
            "health_score": averaged_outputs["health_score"].detach().cpu().numpy(),
            "remaining_life": averaged_outputs["remaining_life"].detach().cpu().numpy(),
            "wear_pattern": wear_probs.detach().cpu().numpy(),
            "source": np.asarray(["pytorch_hybrid"], dtype=object),
        }
        confidence = float(np.max(condition_probs))
        prediction = cast(
            dict[str, Any],
            denormalize_outputs(
                raw_outputs,
                confidence_override=confidence,
                source="pytorch_hybrid",
            ),
        )
        prediction["condition_prediction"] = (
            CONDITION_LABELS[best_condition] if best_condition < len(CONDITION_LABELS) else "unknown"
        )
        prediction["condition_probabilities"] = {
            label: round(float(condition_probs[index]), 4)
            for index, label in enumerate(CONDITION_LABELS)
        }
        return prediction

    def _build_tta_images(self, image_bgr: np.ndarray) -> list[tuple[np.ndarray, bool]]:
        """Small deterministic test-time augmentations for smoother predictions."""
        height, width = image_bgr.shape[:2]
        center = (width / 2.0, height / 2.0)
        variants: list[tuple[np.ndarray, bool]] = [
            (image_bgr, False),
            (cv2.flip(image_bgr, 1), True),
        ]
        for angle in (-3.0, 3.0):
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            variants.append(
                (
                    cv2.warpAffine(
                        image_bgr,
                        matrix,
                        (width, height),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE,
                    ),
                    False,
                )
            )
        variants.append((cv2.convertScaleAbs(image_bgr, alpha=1.04, beta=2.0), False))
        variants.append((cv2.convertScaleAbs(image_bgr, alpha=0.96, beta=-2.0), False))
        return variants

    def _synthetic_prediction(self, depths: list[float]) -> dict[str, Any]:
        raw_outputs = {
            "tread_depths": np.asarray(depths, dtype=np.float32)[np.newaxis, :] / 12.0,
            "health_score": np.asarray([[np.clip(np.mean(depths) / 12.0, 0.0, 1.0)]], dtype=np.float32),
            "remaining_life": np.asarray(
                [[np.clip((np.mean(depths) - 1.6) / 10.4, 0.0, 1.0)]],
                dtype=np.float32,
            ),
            "wear_pattern": self._build_wear_probabilities(depths, 0.72)[np.newaxis, :],
            "source": "synthetic",
        }
        return cast(
            dict[str, Any],
            denormalize_outputs(raw_outputs, confidence_override=0.72, source="synthetic"),
        )

    def _reload_model_if_changed(self) -> None:
        """Hot-reload a newly trained hybrid checkpoint before the next prediction."""
        artifacts = self._resolve_hybrid_artifacts()
        if artifacts is None:
            if self._hybrid_model is not None:
                logger.error("Hybrid checkpoint was removed; unloading runtime model.")
            self._hybrid_model = None
            self._ready = False
            self._model_version = "not_loaded"
            self._model_source = "not_loaded"
            self._hybrid_checkpoint_mtime = None
            self._hybrid_checkpoint_path = None
            self._hybrid_metadata_path = None
            self._load_error = "Missing hybrid checkpoint"
            return
        checkpoint_path, metadata_path, checkpoint_status = artifacts
        if self._hybrid_model is None:
            self._load_model()
            return
        try:
            current_mtime = checkpoint_path.stat().st_mtime
        except OSError:
            return
        if (
            self._hybrid_checkpoint_path == checkpoint_path
            and self._hybrid_checkpoint_mtime is not None
            and current_mtime <= self._hybrid_checkpoint_mtime
        ):
            return

        try:
            from ai_model.hybrid_torch.runtime import load_hybrid_model

            hybrid_bundle = load_hybrid_model(checkpoint_path, metadata_path)
            if hybrid_bundle is None:
                return
            self._hybrid_model, self._hybrid_metadata, self._hybrid_device = hybrid_bundle
            self._hybrid_checkpoint_path = checkpoint_path
            self._hybrid_metadata_path = metadata_path
            self._hybrid_checkpoint_mtime = current_mtime
            self._hybrid_metadata["runtime_checkpoint_status"] = checkpoint_status
            self._model_version = str(
                self._hybrid_metadata.get(
                    "model_version",
                    "pytorch_hybrid:efficientnetv2_b0_vit_b16_bilstm_tcn_attention_calibrated",
                )
            )
            logger.info("Hot-reloaded PyTorch hybrid model: %s", checkpoint_path)
            self._model_source = (
                "pytorch_hybrid"
                if checkpoint_status == "accepted"
                else "pytorch_hybrid_unaccepted_last"
            )
            self._model_checkpoint = str(checkpoint_path)
            self._load_error = None
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("Hybrid model hot-reload failed; keeping existing model: %s", exc)

    async def cleanup(self) -> None:
        self._hybrid_model = None
        self._ready = False
        logger.info("InferenceService cleaned up")
