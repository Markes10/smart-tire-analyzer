"""
Temporal feature extraction utilities for tire wear analysis.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict, TypeAlias

import numpy as np
import numpy.typing as npt

try:
    import tensorflow as tf
except ImportError:  # pragma: no cover - optional at runtime
    tf = None  # type: ignore[assignment]


Float32Array: TypeAlias = npt.NDArray[np.float32]
ArrayLikeFloat: TypeAlias = npt.ArrayLike
KerasModel: TypeAlias = Any
WearTrend: TypeAlias = Literal["accelerating", "stable"]
LEGAL_LIMIT_MM = 1.6


class WearVelocityInfo(TypedDict, total=False):
    """Wear-velocity summary statistics."""

    velocity_mm_per_day: float
    days_to_legal_limit: float | None
    current_avg_depth_mm: float
    trend: WearTrend


# Wear pattern labels
WEAR_PATTERN_CLASSES: dict[int, str] = {
    0: "center_wear",
    1: "edge_wear",
    2: "patchy_wear",
    3: "uniform_wear",
    4: "one_side_wear",
    5: "cupping_wear",
}


def _as_float32_array(values: ArrayLikeFloat) -> Float32Array:
    """Convert array-like inputs to float32 NumPy arrays."""
    return np.asarray(values, dtype=np.float32)


def extract_wear_velocity(
    depth_history: list[list[float]],
    days_history: list[int],
) -> WearVelocityInfo:
    """
    Calculate wear velocity and projected end-of-life from tread history.

    Returns a compact summary with the estimated daily wear rate and, when
    enough data exists, the projected number of days until the legal limit.
    """
    if len(depth_history) < 2:
        return {
            "velocity_mm_per_day": 0.0,
            "days_to_legal_limit": None,
        }

    paired = sorted(
        zip(days_history, depth_history),
        key=lambda item: item[0],
        reverse=True,
    )
    days_arr = np.asarray([float(item[0]) for item in paired], dtype=np.float32)
    depths_arr = np.asarray(
        [float(np.mean(np.asarray(item[1], dtype=np.float32))) for item in paired],
        dtype=np.float32,
    )

    if len(days_arr) >= 2 and float(days_arr[0]) != float(days_arr[-1]):
        slope = np.polyfit(days_arr, depths_arr, 1)
        mm_per_day = float(-slope[0])

        current_depth = float(depths_arr[-1])
        legal_limit = LEGAL_LIMIT_MM

        if mm_per_day > 0.0:
            days_remaining = max(0.0, (current_depth - legal_limit) / mm_per_day)
            days_to_legal_limit: float | None = float(round(days_remaining))
        else:
            days_to_legal_limit = None

        return {
            "velocity_mm_per_day": round(mm_per_day, 4),
            "days_to_legal_limit": days_to_legal_limit,
            "current_avg_depth_mm": round(current_depth, 2),
            "trend": "accelerating" if float(slope[0]) < 0.0 else "stable",
        }

    return {
        "velocity_mm_per_day": 0.0,
        "days_to_legal_limit": None,
    }


def classify_wear_pattern_from_depths(depths: list[float]) -> str:
    """
    Classify a tread wear pattern from four tread depth measurements.

    Tread positions:
        `[inner, inner-center, outer-center, outer]`
    """
    depth_array = _as_float32_array(depths)
    inner_avg = float(np.mean(depth_array[:2]))
    outer_avg = float(np.mean(depth_array[2:]))
    center_avg = float(np.mean(depth_array[1:3]))
    edge_avg = float(np.mean(np.asarray([depth_array[0], depth_array[3]], dtype=np.float32)))

    diff = float(np.max(depth_array) - np.min(depth_array))
    inner_outer_diff = abs(inner_avg - outer_avg)

    if diff < 0.5:
        return WEAR_PATTERN_CLASSES[3]
    if center_avg < edge_avg - 0.8:
        return WEAR_PATTERN_CLASSES[0]
    if edge_avg < center_avg - 0.8:
        return WEAR_PATTERN_CLASSES[1]
    if inner_outer_diff > 1.5:
        return WEAR_PATTERN_CLASSES[4]
    if diff > 2.0:
        return WEAR_PATTERN_CLASSES[2]
    return WEAR_PATTERN_CLASSES[2]


def build_temporal_feature_extractor(
    sequence_dim: int = 8,
    hidden_dim: int = 64,
    output_dim: int = 128,
) -> KerasModel:
    """
    Build a lightweight temporal feature extractor for wear degradation signals.

    Input shape:
        `(batch, time_steps, sequence_dim)`

    Output shape:
        `(batch, output_dim)`
    """
    if tf is None:
        raise RuntimeError("TensorFlow is required to build the temporal feature extractor")
    tf_module: Any = tf
    keras_layers: Any = tf_module.keras.layers
    keras_model: Any = tf_module.keras.Model

    inputs: Any = keras_layers.Input(shape=(None, sequence_dim), name="temporal_input")

    x: Any = keras_layers.Conv1D(
        hidden_dim,
        kernel_size=3,
        padding="causal",
        dilation_rate=1,
        activation="relu",
    )(inputs)
    x = keras_layers.Conv1D(
        hidden_dim,
        kernel_size=3,
        padding="causal",
        dilation_rate=2,
        activation="relu",
    )(x)
    x = keras_layers.LayerNormalization()(x)

    x = keras_layers.LSTM(hidden_dim, return_sequences=True, dropout=0.2)(x)
    x = keras_layers.LSTM(hidden_dim, return_sequences=False, dropout=0.2)(x)

    x = keras_layers.Dense(output_dim, activation="relu")(x)
    x = keras_layers.LayerNormalization()(x)

    return keras_model(inputs=inputs, outputs=x, name="temporal_extractor")


def compute_confidence_from_wear_pattern(
    predicted_depths: ArrayLikeFloat,
    true_depths: ArrayLikeFloat | None = None,
) -> float:
    """
    Compute a confidence score from the internal consistency of tread depths.

    Lower variance and a tighter predicted depth range produce higher scores.
    """
    depths = np.clip(_as_float32_array(predicted_depths), 0.0, 12.0).astype(
        np.float32,
        copy=False,
    )
    depth_std = float(np.std(depths))
    depth_range = float(np.max(depths) - np.min(depths))

    confidence = float(
        np.clip(
            1.0 - (depth_std / 6.0) - (depth_range / 12.0) * 0.3,
            0.1,
            1.0,
        )
    )

    if true_depths is not None:
        true_depth_array = _as_float32_array(true_depths)
        mae = float(np.mean(np.abs(depths - true_depth_array)))
        confidence *= float(np.clip(1.0 - mae / 6.0, 0.0, 1.0))

    return round(confidence, 4)
