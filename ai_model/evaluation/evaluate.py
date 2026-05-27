"""
Model Evaluation - Runs full validation and test set evaluation.
Generates metric reports, prediction samples, and exports CSV summaries.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

from ai_model.evaluation.metrics import compute_all_metrics

logger = logging.getLogger(__name__)

EVAL_OUTPUT_DIR = Path("logs/inference")
EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PathLike: TypeAlias = str | Path
NumpyArray: TypeAlias = npt.NDArray[Any]
TensorMap: TypeAlias = Mapping[str, tf.Tensor]
ArrayMap: TypeAlias = dict[str, NumpyArray]
BatchStore: TypeAlias = dict[str, list[NumpyArray]]
EvaluationReport: TypeAlias = dict[str, Any]


def _to_numpy_array(value: Any) -> NumpyArray:
    """Convert tensors or array-like values to NumPy arrays for evaluation."""
    if hasattr(value, "numpy"):
        return np.asarray(value.numpy())
    return np.asarray(value)


def _init_batch_store() -> BatchStore:
    return {
        "tread_depths": [],
        "health_score": [],
        "remaining_life": [],
        "wear_pattern": [],
    }


def run_evaluation(
    model: Any,
    dataset: Any,
    split_name: str = "test",
    output_dir: PathLike | None = None,
) -> EvaluationReport:
    """
    Run full evaluation on a dataset split.

    Args:
        model: Trained SmartTireModel
        dataset: tf.data.Dataset yielding (inputs, labels) batches
        split_name: "val" or "test"
        output_dir: Where to save evaluation reports

    Returns:
        Dict of aggregated metrics
    """
    output_dir_path = Path(output_dir) if output_dir is not None else EVAL_OUTPUT_DIR
    output_dir_path.mkdir(parents=True, exist_ok=True)

    logger.info("Running evaluation on %s split...", split_name)

    all_predictions = _init_batch_store()
    all_labels = _init_batch_store()

    total_samples = 0
    for batch_inputs_raw, batch_labels_raw in dataset:
        batch_inputs = cast(TensorMap, batch_inputs_raw)
        batch_labels = cast(TensorMap, batch_labels_raw)
        preds = cast(TensorMap, model(batch_inputs, training=False))

        batch_size = int(tf.shape(batch_inputs["image"])[0].numpy())
        total_samples += batch_size

        for key in all_predictions:
            pred_value = preds.get(key)
            if pred_value is not None:
                all_predictions[key].append(_to_numpy_array(pred_value))

            label_value = batch_labels.get(key)
            if label_value is not None:
                all_labels[key].append(_to_numpy_array(label_value))

    pred_arrays: ArrayMap = {
        key: np.concatenate(batches, axis=0)
        for key, batches in all_predictions.items()
        if batches
    }
    label_arrays: ArrayMap = {
        key: np.concatenate(batches, axis=0)
        for key, batches in all_labels.items()
        if batches
    }

    evaluation_summary: EvaluationReport = dict(compute_all_metrics(label_arrays, pred_arrays))
    evaluation_summary["split"] = split_name
    evaluation_summary["total_samples"] = total_samples
    evaluation_summary["evaluated_at"] = datetime.now(timezone.utc).isoformat()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = output_dir_path / f"eval_{split_name}_{timestamp}.json"
    with report_path.open("w", encoding="utf-8") as file_obj:
        json.dump(evaluation_summary, file_obj, indent=2)

    logger.info("Evaluation complete (%s samples):", total_samples)
    for key, value in evaluation_summary.items():
        if isinstance(value, float):
            logger.info("  %s: %s", key, value)

    return evaluation_summary


def evaluate_single_image(
    model: Any,
    image: npt.ArrayLike,
    tread_sequence: npt.ArrayLike,
    context: npt.ArrayLike | None = None,
) -> EvaluationReport:
    """
    Run inference + post-processing on a single preprocessed image.

    Args:
        model: SmartTireModel
        image: (224, 224, 4) preprocessed image
        tread_sequence: (4, 64) tread feature sequence
        context: (64,) context features (optional)

    Returns:
        Full analysis report dict (denormalized)
    """
    from ai_model.ann.output_heads import build_final_report

    image_arr = np.asarray(image, dtype=np.float32)
    tread_sequence_arr = np.asarray(tread_sequence, dtype=np.float32)
    context_arr = (
        np.asarray(context, dtype=np.float32)
        if context is not None
        else np.zeros(64, dtype=np.float32)
    )

    inputs: dict[str, tf.Tensor] = {
        "image": tf.expand_dims(tf.convert_to_tensor(image_arr, dtype=tf.float32), 0),
        "tread_sequence": tf.expand_dims(tf.convert_to_tensor(tread_sequence_arr, dtype=tf.float32), 0),
        "context": tf.expand_dims(tf.convert_to_tensor(context_arr, dtype=tf.float32), 0),
    }

    raw_preds = cast(TensorMap, model(inputs, training=False))
    raw_dict: ArrayMap = {
        key: _to_numpy_array(value)
        for key, value in raw_preds.items()
    }

    return build_final_report(raw_dict)


def load_model_and_evaluate(
    model_path: PathLike,
    dataset_path: PathLike,
    split: str = "test",
) -> EvaluationReport:
    """
    Load model from path and evaluate on dataset.
    Convenience function for evaluation scripts.
    """
    logger.info("Loading model: %s", model_path)
    keras_models = cast(Any, tf.keras.models)
    loaded_model: Any = keras_models.load_model(str(model_path))
    model_name = str(getattr(loaded_model, "name", "unknown"))
    logger.info("Model loaded successfully: %s", model_name)

    dataset_path_obj = Path(dataset_path)
    logger.info("Building %s dataset from: %s", split, dataset_path_obj)
    logger.warning("Dataset loading not implemented in eval script - use train.py datasets")

    return {
        "status": "dataset_loading_not_implemented",
        "model_name": model_name,
        "model_path": str(model_path),
        "dataset_path": str(dataset_path_obj),
        "split": split,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate Smart Tire Model")
    parser.add_argument("--model", required=True, help="Model path (.h5 or SavedModel)")
    parser.add_argument("--dataset", required=True, help="Dataset directory")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--output", default="logs/inference", help="Output directory")
    args = parser.parse_args()

    results = load_model_and_evaluate(args.model, args.dataset, args.split)
    print(json.dumps(results, indent=2))
