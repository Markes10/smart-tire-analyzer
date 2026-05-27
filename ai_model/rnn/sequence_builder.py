"""
Sequence builders for RNN tread analysis.
"""

from __future__ import annotations

from typing import TypedDict, TypeAlias

import numpy as np
import numpy.typing as npt


Float32Array: TypeAlias = npt.NDArray[np.float32]
ArrayLikeFloat: TypeAlias = npt.ArrayLike
TreadDepths: TypeAlias = list[float]
TREAD_SEQUENCE_LENGTH = 4
MULTI_SESSION_FEATURE_DIM = 8


class SessionRecord(TypedDict, total=False):
    """Historical scan data used to build multi-session sequences."""

    tread_depths: TreadDepths
    days_ago: float
    mileage: float


class NormalizedTreadStats(TypedDict):
    """Normalized tread depth summary statistics."""

    tread_1: float
    tread_2: float
    tread_3: float
    tread_4: float
    average: float
    min: float
    max: float
    differential: float
    pct_above_legal: float
    health_fraction: float


# Tread measurement positions (standard 4-point measurement)
TREAD_POSITIONS = ["tread_1", "tread_2", "tread_3", "tread_4"]

# Normal tread depth range limits (in mm)
TREAD_MIN_MM = 0.0
TREAD_MAX_MM = 12.0
LEGAL_LIMIT_MM = 1.6
WARNING_MM = 3.0


def _as_float32_vector(values: ArrayLikeFloat) -> Float32Array:
    """Convert a feature vector into a 1D float32 array."""
    array = np.asarray(values, dtype=np.float32)
    flattened = np.ravel(array).astype(np.float32, copy=False)
    return flattened


def _as_tread_depth_array(depths: TreadDepths) -> Float32Array:
    """Convert tread depth readings into a clipped float32 array."""
    array = np.asarray(depths, dtype=np.float32)
    clipped = np.clip(array, TREAD_MIN_MM, TREAD_MAX_MM).astype(np.float32, copy=False)
    return clipped


def _broadcast_feature_vector(vector: ArrayLikeFloat) -> Float32Array:
    """Broadcast a 1D feature vector to the 4-step tread sequence length."""
    feature_vector = _as_float32_vector(vector)
    expanded = np.expand_dims(feature_vector, axis=0)
    broadcast = np.tile(expanded, (TREAD_SEQUENCE_LENGTH, 1)).astype(
        np.float32,
        copy=False,
    )
    return broadcast


def _session_days_key(session: SessionRecord) -> float:
    """Sort sessions by recency using `days_ago`."""
    return float(session.get("days_ago", 0.0))


def build_tread_sequence(
    tread_depths: TreadDepths,
    image_features: ArrayLikeFloat | None = None,
    metadata_features: ArrayLikeFloat | None = None,
    normalize: bool = True,
    target_dim: int | None = None,
) -> Float32Array:
    """
    Build a sequential representation from 4 tread depth measurements.

    Each time step represents one tread measurement position.
    Optional image and metadata features are broadcast across all steps.
    When target_dim is provided, the final feature axis is padded or truncated
    to that width for models that expect a fixed sequence feature size.
    """
    assert len(tread_depths) == TREAD_SEQUENCE_LENGTH, (
        "Exactly 4 tread measurements required"
    )

    depths = np.asarray(tread_depths, dtype=np.float32)
    if float(depths[3]) == 0.0:
        depths[3] = np.float32(float(np.mean(depths[:3])))
    depths = _as_tread_depth_array(depths.tolist())

    depths_norm: Float32Array
    if normalize:
        depths_norm = (depths / np.float32(TREAD_MAX_MM)).astype(np.float32, copy=False)
    else:
        depths_norm = depths.copy()

    avg_depth = float(np.mean(depths))
    wear_diff = float(np.max(depths) - np.min(depths))
    remaining_pct = np.clip(
        (depths - LEGAL_LIMIT_MM) / (TREAD_MAX_MM - LEGAL_LIMIT_MM),
        0.0,
        1.0,
    ).astype(np.float32, copy=False)

    timesteps: list[list[float]] = []
    for i, (depth, remaining) in enumerate(zip(depths_norm.tolist(), remaining_pct.tolist())):
        step_features: list[float] = [
            float(depth),
            float(remaining),
            float(depth < (WARNING_MM / TREAD_MAX_MM)),
            float(depth < (LEGAL_LIMIT_MM / TREAD_MAX_MM)),
            avg_depth / TREAD_MAX_MM,
            wear_diff / TREAD_MAX_MM,
            float(i) / float(TREAD_SEQUENCE_LENGTH - 1),
        ]
        timesteps.append(step_features)

    sequence = np.asarray(timesteps, dtype=np.float32)

    if image_features is not None:
        img_feat_broadcast = _broadcast_feature_vector(image_features)
        sequence = np.concatenate((sequence, img_feat_broadcast), axis=-1).astype(
            np.float32,
            copy=False,
        )

    if metadata_features is not None:
        meta_broadcast = _broadcast_feature_vector(metadata_features)
        sequence = np.concatenate((sequence, meta_broadcast), axis=-1).astype(
            np.float32,
            copy=False,
        )

    if target_dim is not None:
        current_dim = int(sequence.shape[-1])
        if current_dim > target_dim:
            sequence = sequence[:, :target_dim]
        elif current_dim < target_dim:
            padding = np.zeros(
                (sequence.shape[0], target_dim - current_dim),
                dtype=np.float32,
            )
            sequence = np.concatenate((sequence, padding), axis=-1)

    return sequence


def build_multi_session_sequence(
    sessions: list[SessionRecord],
    max_len: int = 10,
    pad: bool = True,
) -> Float32Array:
    """
    Build a temporal sequence from multiple historical tire scans.

    Each step contains the four normalized tread readings plus summary context
    such as average depth, wear differential, age, and mileage.
    """
    sessions_sorted = sorted(sessions, key=_session_days_key, reverse=True)

    feature_seqs: list[Float32Array] = []
    for session in sessions_sorted[-max_len:]:
        depths = session.get("tread_depths", [5.0, 5.0, 5.0, 5.0])
        depths_arr = _as_tread_depth_array(depths)
        depths_norm = (depths_arr / np.float32(TREAD_MAX_MM)).astype(np.float32, copy=False)

        avg = float(np.mean(depths_norm))
        diff = float(np.max(depths_norm) - np.min(depths_norm))
        days_norm = float(min(float(session.get("days_ago", 0.0)) / 365.0, 3.0))
        mileage_norm = float(min(float(session.get("mileage", 0.0)) / 100000.0, 1.0))

        step = np.asarray(
            [*depths_norm.tolist(), avg, diff, days_norm, mileage_norm],
            dtype=np.float32,
        )
        feature_seqs.append(step)

    if not feature_seqs:
        empty_len = max_len if pad else 0
        return np.zeros((empty_len, MULTI_SESSION_FEATURE_DIM), dtype=np.float32)

    if pad and len(feature_seqs) < max_len:
        pad_len = max_len - len(feature_seqs)
        pad_vec = np.zeros_like(feature_seqs[0], dtype=np.float32)
        feature_seqs = [pad_vec.copy() for _ in range(pad_len)] + feature_seqs

    sequence = np.asarray(feature_seqs, dtype=np.float32)
    return sequence


def normalize_tread_depths(depths: TreadDepths) -> NormalizedTreadStats:
    """
    Normalize and validate a list of 4 tread measurements.

    Returns the cleaned tread depths plus summary statistics.
    """
    depth_list: TreadDepths = [float(depth) for depth in depths]
    assert len(depth_list) == TREAD_SEQUENCE_LENGTH

    for i in range(TREAD_SEQUENCE_LENGTH):
        if depth_list[i] <= 0.0:
            non_zero = [depth for depth in depth_list if depth > 0.0]
            replacement = (
                float(np.mean(np.asarray(non_zero, dtype=np.float32)))
                if non_zero
                else 5.0
            )
            depth_list[i] = replacement

    clipped = _as_tread_depth_array(depth_list)
    clipped_values = [float(value) for value in clipped.tolist()]
    avg = float(np.mean(clipped))
    min_depth = float(np.min(clipped))
    max_depth = float(np.max(clipped))
    above_legal = np.asarray(
        [depth > LEGAL_LIMIT_MM for depth in clipped_values],
        dtype=np.float32,
    )

    return {
        "tread_1": clipped_values[0],
        "tread_2": clipped_values[1],
        "tread_3": clipped_values[2],
        "tread_4": clipped_values[3],
        "average": avg,
        "min": min_depth,
        "max": max_depth,
        "differential": max_depth - min_depth,
        "pct_above_legal": float(np.mean(above_legal)),
        "health_fraction": float(avg / TREAD_MAX_MM),
    }
