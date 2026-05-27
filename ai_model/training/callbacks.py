"""
Training callbacks for Smart Tire Analyzer.
Handles checkpointing, early stopping, LR logging, and model versioning.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import datetime, timezone
from typing import Any, TypeAlias, TypedDict, cast

import tensorflow as tf

logger = logging.getLogger(__name__)

CallbackLogs: TypeAlias = Mapping[str, Any] | None
ValidationBatch: TypeAlias = tuple[Any, Any]
ValidationDataset: TypeAlias = Iterable[ValidationBatch]
KerasCallback: TypeAlias = Any
KerasWeights: TypeAlias = list[Any]
JsonObject: TypeAlias = dict[str, object]


class RegistryEntry(TypedDict):
    version: int
    epoch: int
    val_loss: float
    timestamp: str
    checkpoint_path: str


class RegistryFile(TypedDict, total=False):
    versions: list[RegistryEntry]
    latest: RegistryEntry


MetricHistoryEntry: TypeAlias = dict[str, float | int | str]


def _coerce_float(value: object, default: float) -> float:
    """Convert a metric-like value to float with a safe fallback."""
    try:
        if isinstance(value, (int, float, str)):
            return float(value)
        return default
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, default: int) -> int:
    """Convert a metric-like value to int with a safe fallback."""
    try:
        if isinstance(value, (int, float, str)):
            return int(value)
        return default
    except (TypeError, ValueError):
        return default


def _to_json_object(raw_value: object) -> JsonObject | None:
    """Normalize an unknown JSON dictionary to a typed string-keyed mapping."""
    if not isinstance(raw_value, dict):
        return None

    raw_dict = cast(dict[object, object], raw_value)
    normalized: JsonObject = {}
    for key, value in raw_dict.items():
        normalized[str(key)] = value
    return normalized


def _get_log_metric(logs: CallbackLogs, key: str, default: float) -> float:
    """Read a numeric metric from Keras logs."""
    if logs is None:
        return default
    return _coerce_float(logs.get(key), default)


def _set_log_value(logs: CallbackLogs, key: str, value: object) -> None:
    """Write back to Keras logs when the runtime object is mutable."""
    if isinstance(logs, MutableMapping):
        logs[key] = value


def _require_model(callback: tf.keras.callbacks.Callback) -> Any:
    """Return the bound model or raise a clear error when unavailable."""
    model = getattr(callback, "model", None)
    if model is None:
        raise RuntimeError("Callback model is not set.")
    return model


def _load_registry(path: str) -> RegistryFile:
    """Load the model registry from disk, returning a typed default when absent."""
    if not os.path.exists(path):
        return {"versions": []}

    with open(path, encoding="utf-8") as file_obj:
        loaded_object: object = json.load(file_obj)

    loaded = _to_json_object(loaded_object)
    if loaded is None:
        return {"versions": []}

    versions_raw: object = loaded.get("versions", [])
    versions: list[RegistryEntry] = []
    if isinstance(versions_raw, list):
        versions_list = cast(list[object], versions_raw)
        for item in versions_list:
            item_dict = _to_json_object(item)
            if item_dict is None:
                continue

            checkpoint_path = item_dict.get("checkpoint_path")
            if not isinstance(checkpoint_path, str):
                continue

            versions.append(
                {
                    "version": _coerce_int(item_dict.get("version"), len(versions) + 1),
                    "epoch": _coerce_int(item_dict.get("epoch"), 0),
                    "val_loss": _coerce_float(item_dict.get("val_loss"), float("inf")),
                    "timestamp": str(item_dict.get("timestamp", "")),
                    "checkpoint_path": checkpoint_path,
                }
            )

    registry: RegistryFile = {"versions": versions}
    latest_raw: object = loaded.get("latest")
    latest_dict = _to_json_object(latest_raw)
    if latest_dict is not None:
        latest_path = latest_dict.get("checkpoint_path")
        if isinstance(latest_path, str):
            registry["latest"] = {
                "version": _coerce_int(latest_dict.get("version"), len(versions)),
                "epoch": _coerce_int(latest_dict.get("epoch"), 0),
                "val_loss": _coerce_float(latest_dict.get("val_loss"), float("inf")),
                "timestamp": str(latest_dict.get("timestamp", "")),
                "checkpoint_path": latest_path,
            }

    return registry


class SmartTireCheckpoint(tf.keras.callbacks.Callback):
    """
    Custom checkpoint callback with model versioning.
    Saves model weights when val_loss improves, with version metadata.
    """

    def __init__(
        self,
        output_dir: str,
        monitor: str = "val_loss",
        save_best_only: bool = True,
        min_delta: float = 1e-4,
    ) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.monitor = monitor
        self.save_best_only = save_best_only
        self.min_delta = min_delta
        self.best_value = float("inf")
        self.best_epoch = 0
        self.registry_path = os.path.join(
            output_dir,
            "..",
            "saved_models",
            "model_registry.json",
        )
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)

    def on_epoch_end(self, epoch: int, logs: CallbackLogs = None) -> None:
        current = _get_log_metric(logs, self.monitor, float("inf"))

        if current < self.best_value - self.min_delta:
            self.best_value = current
            self.best_epoch = epoch
            ckpt_path = os.path.join(self.output_dir, f"ckpt_epoch_{epoch:03d}.weights.h5")
            model = _require_model(self)
            model.save_weights(ckpt_path)
            logger.info("Checkpoint saved: %s (%s=%.4f)", ckpt_path, self.monitor, current)
            self._update_registry(epoch, current, ckpt_path)

    def _update_registry(self, epoch: int, metric: float, path: str) -> None:
        registry = _load_registry(self.registry_path)
        if "versions" in registry:
            versions = registry["versions"]
        else:
            versions = []
            registry["versions"] = versions

        entry: RegistryEntry = {
            "version": len(versions) + 1,
            "epoch": epoch,
            "val_loss": round(metric, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checkpoint_path": path,
        }

        versions.append(entry)
        registry["latest"] = entry

        with open(self.registry_path, "w", encoding="utf-8") as file_obj:
            json.dump(registry, file_obj, indent=2)


class EarlyStoppingWithRestore(tf.keras.callbacks.Callback):
    """
    Early stopping with best-weights restore.
    Stops training if val_loss doesn't improve for `patience` epochs,
    then restores the best weights automatically.
    """

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 1e-4,
        restore_best_weights: bool = True,
    ) -> None:
        super().__init__()
        self.patience = patience
        self.min_delta = min_delta
        self.restore_best_weights = restore_best_weights
        self.best_weights: KerasWeights | None = None
        self.best_loss = float("inf")
        self.wait = 0

    def on_epoch_end(self, epoch: int, logs: CallbackLogs = None) -> None:
        current = _get_log_metric(logs, "val_loss", float("inf"))
        model = _require_model(self)

        if current < self.best_loss - self.min_delta:
            self.best_loss = current
            self.wait = 0
            if self.restore_best_weights:
                self.best_weights = list(model.get_weights())
            return

        self.wait += 1
        if self.wait >= self.patience:
            model.stop_training = True
            logger.info("Early stopping triggered at epoch %d.", epoch)
            if self.restore_best_weights and self.best_weights is not None:
                model.set_weights(self.best_weights)
                logger.info("Best weights restored.")


class MetricsLogger(tf.keras.callbacks.Callback):
    """Log all training metrics to a JSON file for each epoch."""

    def __init__(self, log_path: str) -> None:
        super().__init__()
        self.log_path = log_path
        self.history: list[MetricHistoryEntry] = []

    def on_epoch_end(self, epoch: int, logs: CallbackLogs = None) -> None:
        entry: MetricHistoryEntry = {
            "epoch": epoch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        log_items = () if logs is None else logs.items()
        for key, value in log_items:
            if key == "low_confidence_count":
                entry[key] = int(value)
            else:
                entry[key] = float(value)

        self.history.append(entry)
        with open(self.log_path, "w", encoding="utf-8") as file_obj:
            json.dump(self.history, file_obj, indent=2)


class LearningRateLogger(tf.keras.callbacks.Callback):
    """Log the current learning rate at each epoch."""

    def on_epoch_end(self, epoch: int, logs: CallbackLogs = None) -> None:
        model = _require_model(self)
        optimizer = getattr(model, "optimizer", None)
        if optimizer is None:
            logger.debug("Epoch %d - optimizer is unavailable.", epoch)
            return

        lr = optimizer.learning_rate
        if callable(lr):
            lr_val = _coerce_float(lr(optimizer.iterations), 0.0)
        else:
            lr_val = _coerce_float(lr, 0.0)

        _set_log_value(logs, "lr", lr_val)
        logger.debug("Epoch %d - LR: %.8f", epoch, lr_val)


class ConfidenceMonitor(tf.keras.callbacks.Callback):
    """
    Monitor prediction confidence on the validation set.
    Triggers wrong-prediction logging if confidence drops below threshold.
    """

    def __init__(
        self,
        val_ds: ValidationDataset,
        confidence_threshold: float = 0.7,
        log_dir: str = "logs/",
    ) -> None:
        super().__init__()
        self.val_ds = val_ds
        self.threshold = confidence_threshold
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def on_epoch_end(self, epoch: int, logs: CallbackLogs = None) -> None:
        if epoch % 5 != 0:
            return

        model = _require_model(self)
        low_conf_count = 0

        for inputs, _labels in self.val_ds:
            preds: Any = model(inputs, training=False)
            wear_probs = preds["wear_pattern"]
            confidence = tf.reduce_max(wear_probs, axis=-1)
            low_conf_count += int(
                tf.reduce_sum(tf.cast(confidence < self.threshold, tf.int32))
            )

        logger.info(
            "Epoch %d - Low confidence predictions: %d",
            epoch,
            low_conf_count,
        )
        _set_log_value(logs, "low_confidence_count", low_conf_count)


def build_callbacks(
    output_dir: str,
    patience: int = 10,
    val_ds: ValidationDataset | None = None,
) -> list[KerasCallback]:
    """
    Build the complete callback list for training.

    Args:
        output_dir: Directory for checkpoints and logs.
        patience: Early stopping patience.
        val_ds: Validation dataset for confidence monitoring.

    Returns:
        List of configured callbacks.
    """
    os.makedirs(output_dir, exist_ok=True)
    log_dir = os.path.join(output_dir, "..", "..", "logs", "training")
    os.makedirs(log_dir, exist_ok=True)

    tf_module: Any = tf
    callbacks_module: Any = tf_module.keras.callbacks

    callbacks: list[KerasCallback] = [
        SmartTireCheckpoint(output_dir=output_dir),
        EarlyStoppingWithRestore(patience=patience),
        LearningRateLogger(),
        MetricsLogger(log_path=os.path.join(log_dir, "metrics.json")),
        callbacks_module.TensorBoard(
            log_dir=log_dir,
            histogram_freq=1,
            update_freq="epoch",
        ),
    ]

    if val_ds is not None:
        callbacks.append(ConfidenceMonitor(val_ds=val_ds, log_dir=log_dir))

    return callbacks
