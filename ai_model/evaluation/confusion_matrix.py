"""
Confusion Matrix & Classification Report for Wear Pattern Detection.
Generates detailed per-class analysis of wear pattern classification.
"""

from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

WEAR_LABELS: list[str] = [
    "center_wear",
    "edge_wear",
    "patchy_wear",
    "uniform_wear",
    "one_side_wear",
    "cupping_wear",
]

WEAR_DISPLAY_NAMES: dict[str, str] = {
    "center_wear": "Center Wear\n(Overinflation)",
    "edge_wear": "Edge Wear\n(Underinflation)",
    "patchy_wear": "Patchy Wear\n(Misalignment)",
    "uniform_wear": "Uniform Wear\n(Normal)",
    "one_side_wear": "One-Side Wear\n(Camber Issue)",
    "cupping_wear": "Cupping Wear\n(Suspension)",
}

PathLike: TypeAlias = str | Path
LabelArray: TypeAlias = npt.NDArray[np.int64]
ProbabilityArray: TypeAlias = npt.NDArray[np.float64]
ConfusionMatrixArray: TypeAlias = npt.NDArray[np.int32]
DisplayMatrixArray: TypeAlias = npt.NDArray[np.float64]
MetricDict: TypeAlias = dict[str, float | int]
ClassificationReport: TypeAlias = dict[str, MetricDict | float]
GeneratedArtifacts: TypeAlias = dict[str, ClassificationReport | str]


def _as_label_array(y_true: npt.ArrayLike) -> LabelArray:
    return np.asarray(y_true, dtype=np.int64).reshape(-1)


def _as_probability_array(y_pred_probs: npt.ArrayLike) -> ProbabilityArray:
    return np.asarray(y_pred_probs, dtype=np.float64)


def _load_pyplot() -> Any:
    """Import matplotlib lazily so evaluation metrics work without plotting deps."""
    try:
        matplotlib = cast(Any, importlib.import_module("matplotlib"))
        matplotlib.use("Agg")
        return cast(Any, importlib.import_module("matplotlib.pyplot"))
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "matplotlib is required to plot confusion matrices. "
            "Install it in the project virtual environment to enable plotting."
        ) from exc


def build_confusion_matrix(
    y_true: npt.ArrayLike,
    y_pred_probs: npt.ArrayLike,
    num_classes: int = 6,
) -> ConfusionMatrixArray:
    """
    Build raw confusion matrix.

    Args:
        y_true: Ground truth class labels (N,)
        y_pred_probs: Predicted softmax probabilities (N, num_classes)

    Returns:
        Confusion matrix: (num_classes, num_classes) - row=actual, col=predicted
    """
    y_true_arr = _as_label_array(y_true)
    y_pred_probs_arr = _as_probability_array(y_pred_probs)
    y_pred = np.argmax(y_pred_probs_arr, axis=-1).astype(np.int64, copy=False)

    cm: ConfusionMatrixArray = np.zeros((num_classes, num_classes), dtype=np.int32)
    for true_label, pred_label in zip(y_true_arr.tolist(), y_pred.tolist()):
        cm[true_label, pred_label] += 1
    return cm


def compute_classification_report(
    y_true: npt.ArrayLike,
    y_pred_probs: npt.ArrayLike,
) -> ClassificationReport:
    """
    Compute per-class precision, recall, F1-score.

    Returns:
        Dict with per-class and macro-averaged metrics
    """
    cm = build_confusion_matrix(y_true, y_pred_probs)
    n_classes = int(cm.shape[0])
    report: ClassificationReport = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for i, label in enumerate(WEAR_LABELS[:n_classes]):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum()) - tp
        fn = int(cm[i, :].sum()) - tp

        precision = float(tp / max(tp + fp, 1))
        recall = float(tp / max(tp + fn, 1))
        f1 = float(2 * precision * recall / max(precision + recall, 1e-8))
        support = int(cm[i, :].sum())

        report[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": support,
        }
        if support > 0:
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(f1)

    macro_precision = float(np.mean(precisions)) if precisions else 0.0
    macro_recall = float(np.mean(recalls)) if recalls else 0.0
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0

    report["macro_avg"] = {
        "precision": round(macro_precision, 4),
        "recall": round(macro_recall, 4),
        "f1_score": round(macro_f1, 4),
    }

    total = int(cm.sum())
    report["accuracy"] = round(float(np.trace(cm) / max(total, 1)), 4)
    return report


def plot_confusion_matrix(
    y_true: npt.ArrayLike,
    y_pred_probs: npt.ArrayLike,
    output_path: PathLike | None = None,
    normalize: bool = True,
) -> str:
    """
    Generate and save a styled confusion matrix plot.

    Args:
        y_true: Ground truth labels (N,)
        y_pred_probs: Predicted probabilities (N, 6)
        output_path: Where to save the plot
        normalize: If True, show proportions (row-normalized)

    Returns:
        Path to saved plot
    """
    plt = _load_pyplot()
    cm = build_confusion_matrix(y_true, y_pred_probs)

    if normalize:
        row_sums = cm.sum(axis=1, keepdims=True)
        cm_display: DisplayMatrixArray = cm.astype(np.float64, copy=False) / np.maximum(
            row_sums, 1
        )
        title = "Wear Pattern Confusion Matrix (Normalized)"
    else:
        cm_display = cm.astype(np.float64, copy=False)
        title = "Wear Pattern Confusion Matrix (Counts)"

    n = int(cm.shape[0])
    display_labels = [WEAR_DISPLAY_NAMES[label] for label in WEAR_LABELS[:n]]

    fig, ax = plt.subplots(figsize=(10, 8))

    im = ax.imshow(cm_display, interpolation="nearest", cmap=plt.get_cmap("Blues"))
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(display_labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(display_labels, fontsize=9)

    thresh = float(cm_display.max() / 2.0) if cm_display.size else 0.0
    for i in range(n):
        for j in range(n):
            display_value = float(cm_display[i, j])
            text = f"{display_value:.2f}" if normalize else f"{int(cm[i, j])}"
            color = "white" if display_value > thresh else "black"
            ax.text(j, i, text, ha="center", va="center", color=color, fontsize=9)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Predicted Label", fontsize=11, labelpad=10)
    ax.set_ylabel("True Label", fontsize=11, labelpad=10)

    plt.tight_layout()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path_obj = (
        Path(output_path)
        if output_path is not None
        else Path("logs/inference") / f"confusion_matrix_{timestamp}.png"
    )
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_path_obj, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Confusion matrix saved: %s", output_path_obj)
    return str(output_path_obj)


def generate_full_classification_report(
    y_true: npt.ArrayLike,
    y_pred_probs: npt.ArrayLike,
    output_dir: PathLike = "logs/inference",
) -> GeneratedArtifacts:
    """
    Generate and save both the confusion matrix plot and classification JSON report.

    Returns:
        Dict with report data and plot path
    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    report = compute_classification_report(y_true, y_pred_probs)
    cm_path = plot_confusion_matrix(
        y_true,
        y_pred_probs,
        output_path=output_dir_path / "confusion_matrix.png",
    )

    report_path = output_dir_path / "classification_report.json"
    with report_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, indent=2)

    logger.info("Classification report saved: %s", report_path)

    return {
        "report": report,
        "confusion_matrix_plot": cm_path,
        "report_json": str(report_path),
    }
