"""
Continuous-learning dataset refresh and retrain trigger.

Feedback corrections are saved by the API. This module keeps the generated
dataset current and starts a real hybrid retraining job once enough trainable
corrections have accumulated.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRONG_PREDICTIONS_DIR = PROJECT_ROOT / "continuous_learning" / "wrong_predictions"
CONTINUOUS_LABELS_CSV = PROJECT_ROOT / "dataset" / "continuous_learning" / "labels.csv"
STATUS_PATH = PROJECT_ROOT / "continuous_learning" / "retraining" / "status.json"

_refresh_thread: threading.Thread | None = None
_retrain_thread: threading.Thread | None = None
_worker_lock = threading.Lock()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_status(status: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, default=str), encoding="utf-8")


def _has_tread_value(row: dict[str, str]) -> bool:
    for key in ("tread_1", "tread_2", "tread_3", "tread_4", "tread_average"):
        if str(row.get(key, "")).strip():
            return True
    return False


def _has_existing_image(row: dict[str, str]) -> bool:
    image_path = str(row.get("image_path", "")).strip()
    if not image_path:
        return False
    path = Path(image_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.is_file()


def count_trainable_learning_rows() -> int:
    """Count app-corrected samples that have both an image path and tread labels."""
    if not CONTINUOUS_LABELS_CSV.exists():
        return 0
    try:
        with CONTINUOUS_LABELS_CSV.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return sum(
                1
                for row in reader
                if _has_existing_image(row) and _has_tread_value(row)
            )
    except Exception as exc:
        logger.warning("Could not count continuous-learning labels: %s", exc)
        return 0


def get_retrain_status() -> dict[str, Any]:
    """Return retraining state for API/status screens."""
    status = _load_status()
    trainable_rows = count_trainable_learning_rows()
    threshold = _env_int("RETRAIN_THRESHOLD", 10)
    last_trained_rows = int(status.get("last_trained_learning_rows", 0) or 0)
    pending_rows = max(0, trainable_rows - last_trained_rows)
    status.update(
        {
            "trainable_learning_rows": trainable_rows,
            "pending_learning_rows": pending_rows,
            "retrain_threshold": threshold,
            "auto_retrain": _env_bool("AUTO_RETRAIN", True),
            "auto_retrain_train": _env_bool("AUTO_RETRAIN_TRAIN", True),
            "auto_retrain_refresh": _env_bool("AUTO_RETRAIN_REFRESH", False),
            "refresh_running": _refresh_thread is not None and _refresh_thread.is_alive(),
            "retrain_running": _retrain_thread is not None and _retrain_thread.is_alive(),
        }
    )
    return status


async def schedule_learning_refresh() -> bool:
    """
    Refresh generated dataset artifacts in the background.

    Returns True when a new refresh task was scheduled.
    """
    global _refresh_thread
    if count_trainable_learning_rows() == 0:
        return False
    with _worker_lock:
        if _refresh_thread is not None and _refresh_thread.is_alive():
            return False
        _refresh_thread = threading.Thread(
            target=_run_refresh_pipeline_thread,
            daemon=True,
            name="ContinuousLearningRefresh",
        )
        _refresh_thread.start()
        return True


async def check_and_trigger_retrain() -> bool:
    """
    Trigger retraining when enough new corrected image rows exist.

    Returns True when a retrain task was scheduled.
    """
    global _retrain_thread
    try:
        trainable_rows = count_trainable_learning_rows()
        threshold = _env_int("RETRAIN_THRESHOLD", 10)
        status = _load_status()
        last_trained_rows = int(status.get("last_trained_learning_rows", 0) or 0)
        pending_rows = max(0, trainable_rows - last_trained_rows)

        logger.info(
            "Continuous-learning rows: pending=%s total=%s threshold=%s",
            pending_rows,
            trainable_rows,
            threshold,
        )

        if pending_rows <= 0:
            return False

        if not _env_bool("AUTO_RETRAIN", True):
            if _env_bool("AUTO_RETRAIN_REFRESH", False):
                await schedule_learning_refresh()
            return False

        if pending_rows < threshold:
            if _env_bool("AUTO_RETRAIN_REFRESH", False):
                await schedule_learning_refresh()
            return False

        with _worker_lock:
            if _retrain_thread is not None and _retrain_thread.is_alive():
                logger.info("Retrain already running; skipping duplicate trigger.")
                return False
            _retrain_thread = threading.Thread(
                target=_run_retrain_pipeline_thread,
                args=(trainable_rows, pending_rows),
                daemon=True,
                name="ContinuousLearningRetrain",
            )
            _retrain_thread.start()
            return True

    except Exception as exc:
        logger.error("Retrain check failed: %s", exc)
        return False


def _run_refresh_pipeline_thread() -> None:
    try:
        result = _refresh_sync()
    except Exception as exc:
        logger.exception("Dataset refresh failed.")
        result = {"status": "error", "reason": str(exc), "finished_at": _now()}
    status = _load_status()
    status["last_dataset_refresh"] = result
    status["last_dataset_refresh_at"] = _now()
    _save_status(status)


def _refresh_sync() -> dict[str, Any]:
    from continuous_learning.retraining.incremental_train import refresh_prepared_dataset

    logger.info("Refreshing prepared dataset from continuous-learning labels.")
    return refresh_prepared_dataset(PROJECT_ROOT)


def _run_retrain_pipeline_thread(trainable_rows: int, pending_rows: int) -> None:
    status = _load_status()
    status.update(
        {
            "last_retrain_started_at": _now(),
            "last_retrain_status": "running",
            "last_retrain_pending_rows": pending_rows,
            "last_retrain_trainable_rows": trainable_rows,
        }
    )
    _save_status(status)

    result = _retrain_sync()

    status = _load_status()
    status["last_retrain_finished_at"] = _now()
    status["last_retrain_result"] = result
    status["last_retrain_status"] = result.get("status", "unknown")
    if result.get("status") in {"success", "prepared_only"}:
        status["last_trained_learning_rows"] = trainable_rows
    _save_status(status)


def _retrain_sync() -> dict[str, Any]:
    try:
        from continuous_learning.retraining.incremental_train import run_incremental_training

        logger.info("Starting automatic continuous-learning retraining.")
        return run_incremental_training(
            data_dir=str(WRONG_PREDICTIONS_DIR),
            max_epochs=3,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        logger.exception("Retraining failed.")
        return {"status": "error", "reason": str(exc), "finished_at": _now()}
