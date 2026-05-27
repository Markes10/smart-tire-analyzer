"""
Evaluation Metrics - MAE, RMSE, accuracy per output head.
Used during training validation and final test set evaluation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias

import numpy as np
import numpy.typing as npt


WEAR_LABELS = [
    "center_wear",
    "edge_wear",
    "patchy_wear",
    "uniform_wear",
    "one_side_wear",
    "cupping_wear",
]
TREAD_MAX_MM = 12.0
HEALTH_MAX = 10.0
REMAINING_MAX_KM = 80000.0

FloatArray: TypeAlias = npt.NDArray[np.float64]
IntArray: TypeAlias = npt.NDArray[np.int64]
MetricMap: TypeAlias = dict[str, float]
PerClassMetricMap: TypeAlias = dict[str, float | None]
ArrayDict: TypeAlias = Mapping[str, npt.ArrayLike]

from ai_model.classes import classify_tread_depth, TreadDepthClass


def _as_float_array(values: npt.ArrayLike) -> FloatArray:
    return np.asarray(values, dtype=np.float64)


def _as_label_array(values: npt.ArrayLike) -> IntArray:
    return np.asarray(values, dtype=np.int64).reshape(-1)


def _as_mm_values(values: npt.ArrayLike, max_value: float) -> FloatArray:
    array = _as_float_array(values)
    if array.size == 0:
        return array
    if float(np.min(array)) >= -0.05 and float(np.max(array)) <= 1.05 and max_value > 1.0:
        return array * max_value
    return array


def tread_mae_mm(y_true: npt.ArrayLike, y_pred: npt.ArrayLike) -> float:
    """Mean Absolute Error for tread depth predictions (in mm)."""
    true_mm = _as_mm_values(y_true, TREAD_MAX_MM)
    pred_mm = _as_mm_values(y_pred, TREAD_MAX_MM)
    return float(np.mean(np.abs(true_mm - pred_mm)))


def tread_rmse_mm(y_true: npt.ArrayLike, y_pred: npt.ArrayLike) -> float:
    """Root Mean Squared Error for tread depth predictions (in mm)."""
    true_mm = _as_mm_values(y_true, TREAD_MAX_MM)
    pred_mm = _as_mm_values(y_pred, TREAD_MAX_MM)
    return float(np.sqrt(np.mean((true_mm - pred_mm) ** 2)))


def health_mae(y_true: npt.ArrayLike, y_pred: npt.ArrayLike) -> float:
    """MAE for health score predictions (0-10 scale)."""
    y_true_arr = _as_mm_values(y_true, HEALTH_MAX)
    y_pred_arr = _as_mm_values(y_pred, HEALTH_MAX)
    return float(np.mean(np.abs(y_true_arr - y_pred_arr)))


def remaining_life_mae_km(y_true: npt.ArrayLike, y_pred: npt.ArrayLike) -> float:
    """MAE for remaining life predictions (in km)."""
    y_true_arr = _as_mm_values(y_true, REMAINING_MAX_KM)
    y_pred_arr = _as_mm_values(y_pred, REMAINING_MAX_KM)
    return float(np.mean(np.abs(y_true_arr - y_pred_arr)))


def wear_pattern_accuracy(y_true: npt.ArrayLike, y_pred_probs: npt.ArrayLike) -> float:
    """Classification accuracy for wear pattern predictions."""
    y_true_arr = _as_label_array(y_true)
    y_pred_probs_arr = _as_float_array(y_pred_probs)
    y_pred_class = np.argmax(y_pred_probs_arr, axis=-1).astype(np.int64, copy=False)
    correct = int(np.count_nonzero(y_true_arr == y_pred_class))
    return float(correct / max(y_true_arr.size, 1))


def wear_pattern_per_class_accuracy(
    y_true: npt.ArrayLike,
    y_pred_probs: npt.ArrayLike,
) -> PerClassMetricMap:
    """Per-class accuracy for each wear pattern type."""
    y_true_arr = _as_label_array(y_true)
    y_pred_probs_arr = _as_float_array(y_pred_probs)
    y_pred = np.argmax(y_pred_probs_arr, axis=-1).astype(np.int64, copy=False)
    results: PerClassMetricMap = {}

    for i, label in enumerate(WEAR_LABELS):
        mask = y_true_arr == i
        if int(mask.sum()) > 0:
            class_total = int(mask.sum())
            class_correct = int(np.count_nonzero(y_pred[mask] == i))
            results[label] = float(class_correct / max(class_total, 1))
        else:
            results[label] = None
    return results


def within_threshold_accuracy(
    y_true_mm: npt.ArrayLike,
    y_pred_mm: npt.ArrayLike,
    threshold_mm: float = 0.5,
) -> float:
    """
    Fraction of predictions within +/-threshold_mm of ground truth.
    Key metric for safety-critical tread depth assessment.
    """
    y_true_mm_arr = _as_float_array(y_true_mm)
    y_pred_mm_arr = _as_float_array(y_pred_mm)
    return float(np.mean(np.abs(y_true_mm_arr - y_pred_mm_arr) <= threshold_mm))


def danger_zone_recall(
    y_true_mm: npt.ArrayLike,
    y_pred_mm: npt.ArrayLike,
    danger_threshold: float = 3.0,
) -> float:
    """
    Recall for detecting tires in the danger zone (< 3mm).
    Critical safety metric - false negatives are very dangerous.
    """
    y_true_mm_arr = _as_float_array(y_true_mm)
    y_pred_mm_arr = _as_float_array(y_pred_mm)
    actual_danger = y_true_mm_arr < danger_threshold
    predicted_danger = y_pred_mm_arr < danger_threshold
    if int(actual_danger.sum()) == 0:
        return 1.0
    return float(np.mean(predicted_danger[actual_danger]))


def compute_all_metrics(y_true: ArrayDict, y_pred: ArrayDict) -> MetricMap:
    """
    Compute the full metric suite for all prediction outputs.

    Args:
        y_true: Ground truth dict with:
            tread_depths: (N, 4) normalized [0,1]
            health_score: (N, 1) normalized [0,1]
            remaining_life: (N, 1) normalized [0,1]
            wear_pattern: (N,) integer class labels
        y_pred: Model predictions dict (same format as y_true,
                except wear_pattern is (N, 6) softmax probabilities)

    Returns:
        Dict of all computed metrics
    """
    metrics: MetricMap = {}

    if "tread_depths" in y_true and "tread_depths" in y_pred:
        avg_true = np.mean(_as_float_array(y_true["tread_depths"]), axis=-1)
        avg_pred = np.mean(_as_float_array(y_pred["tread_depths"]), axis=-1)
        true_mm = avg_true * TREAD_MAX_MM
        pred_mm = avg_pred * TREAD_MAX_MM

        metrics["tread_mae_mm"] = tread_mae_mm(avg_true, avg_pred)
        metrics["tread_rmse_mm"] = tread_rmse_mm(avg_true, avg_pred)
        metrics["tread_within_0.5mm"] = within_threshold_accuracy(true_mm, pred_mm, 0.5)
        metrics["tread_within_1.0mm"] = within_threshold_accuracy(true_mm, pred_mm, 1.0)
        metrics["danger_zone_recall"] = danger_zone_recall(true_mm, pred_mm)

        # Classification metrics derived from average tread depth
        try:
            true_classes = np.array([
                classify_tread_depth(mm).value for mm in true_mm.flatten()
            ])
            pred_classes = np.array([
                classify_tread_depth(mm).value for mm in pred_mm.flatten()
            ])
        except Exception:
            # If classification helper not available, skip
            true_classes = None
            pred_classes = None

        if true_classes is not None and pred_classes is not None:
            # overall accuracy
            overall = float(np.mean(true_classes == pred_classes)) if true_classes.size > 0 else 0.0
            metrics["tread_class_accuracy"] = overall

            # per-class accuracy
            for c in TreadDepthClass:
                mask = true_classes == c.value
                if int(mask.sum()) > 0:
                    acc = float(np.mean(pred_classes[mask] == c.value))
                    metrics[f"tread_{c.value}_accuracy"] = acc
                else:
                    metrics[f"tread_{c.value}_accuracy"] = None

    if "health_score" in y_true and "health_score" in y_pred:
        metrics["health_mae"] = health_mae(
            _as_float_array(y_true["health_score"]).flatten(),
            _as_float_array(y_pred["health_score"]).flatten(),
        )

    if "remaining_life" in y_true and "remaining_life" in y_pred:
        metrics["remaining_life_mae_km"] = remaining_life_mae_km(
            _as_float_array(y_true["remaining_life"]).flatten(),
            _as_float_array(y_pred["remaining_life"]).flatten(),
        )

    if "wear_pattern" in y_true and "wear_pattern" in y_pred:
        metrics["wear_accuracy"] = wear_pattern_accuracy(
            y_true["wear_pattern"],
            y_pred["wear_pattern"],
        )
        per_class = wear_pattern_per_class_accuracy(
            y_true["wear_pattern"],
            y_pred["wear_pattern"],
        )
        for cls, acc in per_class.items():
            if acc is not None:
                metrics[f"wear_{cls}_accuracy"] = acc

    # Round numeric metrics, leave None (missing per-class metrics) untouched
    out: dict[str, float | None] = {}
    for key, value in metrics.items():
        if value is None:
            out[key] = None
        else:
            try:
                out[key] = round(float(value), 4)
            except Exception:
                out[key] = value
    return out
