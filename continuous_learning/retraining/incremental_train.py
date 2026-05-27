"""
Automatic retraining for continuous-learning samples.

The old implementation trained a placeholder TensorFlow model on random arrays.
This module now refreshes the real prepared dataset and, when enabled, launches
the active PyTorch hybrid training command in a background-safe subprocess.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "continuous_learning" / "retraining" / "runs"


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


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def refresh_prepared_dataset(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Rebuild generated dataset artifacts, including continuous-learning rows."""
    from scripts.prepare_dataset import DatasetPaths, prepare_dataset

    manifest = prepare_dataset(paths=DatasetPaths(root=project_root / "dataset"))
    return {
        "status": "prepared",
        "manifest_path": _relative(project_root / "dataset" / "metadata" / "dataset_manifest.json", project_root),
        "processed_rows": manifest.get("row_counts", {}).get("processed_rows"),
        "front_matched": manifest.get("image_matching", {}).get("front_matched"),
        "learning_labels": manifest.get("learning_labels", []),
    }


def build_training_command(project_root: Path = PROJECT_ROOT) -> list[str]:
    """Build the real hybrid training command from environment settings."""
    command = [
        sys.executable,
        str(project_root / "scripts" / "prepare_and_train.py"),
        "--fresh-hybrid",
    ]

    if _env_bool("AUTO_RETRAIN_FULL_TRAIN", True):
        command.append("--full-train")
    if _env_bool("AUTO_RETRAIN_ARCHIVE_OLD", False):
        command.append("--archive-old")

    stage1_epochs = _env_int("AUTO_RETRAIN_STAGE1_EPOCHS", 2)
    stage2_epochs = _env_int("AUTO_RETRAIN_STAGE2_EPOCHS", 1)
    batch_size = _env_int("AUTO_RETRAIN_BATCH_SIZE", 2)
    stage2_batch_size = _env_int("AUTO_RETRAIN_STAGE2_BATCH_SIZE", 1)
    grad_accum_steps = _env_int("AUTO_RETRAIN_GRAD_ACCUM_STEPS", 8)

    command.extend(
        [
            "--hybrid-stage1-epochs",
            str(stage1_epochs),
            "--hybrid-stage2-epochs",
            str(stage2_epochs),
            "--hybrid-batch-size",
            str(batch_size),
            "--hybrid-stage2-batch-size",
            str(stage2_batch_size),
            "--hybrid-grad-accum-steps",
            str(grad_accum_steps),
        ]
    )
    return command


def _write_run_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_incremental_training(
    data_dir: str,
    max_epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 1e-5,
    project_root: str | Path | None = None,
    train: bool | None = None,
) -> dict[str, Any]:
    """
    Refresh dataset artifacts and optionally launch real hybrid retraining.

    Args kept for backward compatibility with the existing retrain trigger.
    Environment controls:
      AUTO_RETRAIN_TRAIN=false       -> only refresh prepared dataset
      AUTO_RETRAIN_STAGE1_EPOCHS=2   -> quick automatic retraining by default
      AUTO_RETRAIN_STAGE2_EPOCHS=1
    """
    root = Path(project_root or PROJECT_ROOT).resolve()
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    run_log = root / "continuous_learning" / "retraining" / "runs" / f"retrain_{run_id}.json"

    result: dict[str, Any] = {
        "status": "started",
        "started_at": started_at,
        "data_dir": str(data_dir),
        "project_root": str(root),
        "run_log": _relative(run_log, root),
    }

    try:
        result["dataset"] = refresh_prepared_dataset(root)

        train_enabled = _env_bool("AUTO_RETRAIN_TRAIN", True) if train is None else bool(train)
        if not train_enabled:
            result.update(
                {
                    "status": "prepared_only",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "AUTO_RETRAIN_TRAIN=false",
                }
            )
            _write_run_log(run_log, result)
            return result

        command = build_training_command(root)
        result["command"] = command
        logger.info("Starting automatic hybrid retraining: %s", " ".join(command))

        timeout_seconds = _env_int("AUTO_RETRAIN_TIMEOUT_SECONDS", 0)
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds if timeout_seconds > 0 else None,
            check=False,
        )

        result.update(
            {
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if completed.returncode != 0:
            result["status"] = "error"
            result["reason"] = f"Training command failed with exit code {completed.returncode}"
            logger.error("Automatic retraining failed: %s", result["reason"])
        else:
            result["status"] = "success"
            result["model_path"] = _relative(root / "ai_model" / "saved_models" / "hybrid_torch" / "model_best.pt", root)
            logger.info("Automatic retraining completed successfully.")

        _write_run_log(run_log, result)
        return result

    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "error",
                "reason": f"Training timed out after {exc.timeout} seconds",
                "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
                "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_run_log(run_log, result)
        logger.error("Automatic retraining timed out: %s", result["reason"])
        return result
    except Exception as exc:
        result.update(
            {
                "status": "error",
                "reason": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_run_log(run_log, result)
        logger.exception("Automatic retraining failed.")
        return result
