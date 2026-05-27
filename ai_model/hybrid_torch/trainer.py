"""Training pipeline for the fresh PyTorch hybrid tire model."""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from ai_model.hybrid_torch.calibration import (
    IsotonicTreadCalibrator,
    apply_tread_calibration_array,
    fit_isotonic_tread_calibrator,
    save_tread_calibrator,
)
from ai_model.hybrid_torch.constants import (
    CONDITION_LABELS,
    HYBRID_MODEL_VERSION,
    MAX_REMAINING_KM,
    TREAD_MAX_MM,
    WEAR_LABELS,
)
from ai_model.hybrid_torch.dataset import HybridTireDataset, split_summary
from ai_model.hybrid_torch.model import HybridTireModel, count_trainable_parameters
from ai_model.hybrid_torch.runtime_tread import RUNTIME_TREAD_SEQUENCE_SOURCE

logger = logging.getLogger("hybrid_torch_trainer")

MAX_TEST_TREAD_MAE_MM = 1.0
MAX_TEST_AVG_TREAD_MAE_MM = 1.0
MIN_TEST_TREAD_WITHIN_1MM = 0.85
MIXUP_ALPHA = 0.2
MIXUP_PROBABILITY = 0.5


@dataclass
class FreshHybridConfig:
    project_root: Path
    stage1_epochs: int = 8
    stage2_epochs: int = 12
    batch_size: int = 2
    stage2_batch_size: int = 1
    grad_accum_steps: int = 8
    learning_rate: float = 1e-4
    fine_tune_learning_rate: float = 1e-5
    weight_decay: float = 1e-3
    patience: int = 3
    num_workers: int = 0
    pretrained_required: bool = True
    archive_old: bool = False
    tread_sequence_source: str = RUNTIME_TREAD_SEQUENCE_SOURCE
    resume_checkpoint: str | None = None

    @property
    def split_root(self) -> Path:
        return self.project_root / "dataset" / "splits"

    @property
    def output_dir(self) -> Path:
        return self.project_root / "ai_model" / "saved_models" / "hybrid_torch"

    @property
    def saved_models_dir(self) -> Path:
        return self.project_root / "ai_model" / "saved_models"


def archive_legacy_artifacts(saved_models_dir: Path, project_root: Path | None = None) -> Path | None:
    """Move existing saved model artifacts into a timestamped archive directory."""
    saved_models_dir = Path(saved_models_dir)
    if not saved_models_dir.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_root = (project_root or saved_models_dir.parents[1]) / "ai_model" / "model_archive"
    archive_dir = archive_root / f"{timestamp}_legacy"
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved = False
    for item in saved_models_dir.iterdir():
        destination = archive_dir / item.name
        shutil.move(str(item), str(destination))
        moved = True
    return archive_dir if moved else None


def _make_loader(dataset: HybridTireDataset, batch_size: int, shuffle: bool, num_workers: int) -> DataLoader:
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        drop_last=shuffle,
    )


def _move_batch(batch: tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]], device: torch.device) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    inputs, targets = batch
    return (
        {key: value.to(device, non_blocking=True) for key, value in inputs.items()},
        {key: value.to(device, non_blocking=True) for key, value in targets.items()},
    )


def _uncertainty_weighted_loss(
    model: HybridTireModel | None,
    components: dict[str, torch.Tensor],
) -> torch.Tensor:
    if model is None or not hasattr(model, "loss_log_vars"):
        return (
            components["tread"] * 2.5
            + components["health"] * 0.7
            + components["life"] * 0.7
            + components["wear"] * 0.5
            + components["condition"] * 0.4
        )

    total = torch.zeros((), dtype=next(iter(components.values())).dtype, device=next(iter(components.values())).device)
    for name, component in components.items():
        log_var = torch.clamp(model.loss_log_vars[name], min=-3.0, max=3.0)
        total = total + torch.exp(-log_var) * component + 0.5 * log_var
    return total


def _loss(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    model: HybridTireModel | None = None,
) -> torch.Tensor:
    predicted_mm = outputs["tread_depths"] * TREAD_MAX_MM
    target_mm = targets["tread_depths"] * TREAD_MAX_MM

    # Optimize directly around the runtime acceptance gate: no extra penalty
    # inside 1 mm, linear pressure once a prediction misses that threshold.
    error_mm = torch.abs(predicted_mm - target_mm)
    base_l1 = F.smooth_l1_loss(
        predicted_mm,
        target_mm,
        beta=0.5,
        reduction="none",
    )
    exceeds_1mm_penalty = torch.relu(error_mm - 1.0)
    tread_error = base_l1 + 2.0 * exceeds_1mm_penalty

    high_depth_weight = 1.0 + (target_mm >= 5.0).float() + (target_mm >= 6.0).float()
    tread = torch.mean(tread_error * high_depth_weight)
    health = F.mse_loss(outputs["health_score"], targets["health_score"])
    life = F.mse_loss(outputs["remaining_life"], targets["remaining_life"])
    wear = F.cross_entropy(outputs["wear_pattern"], targets["wear_pattern"])
    condition = F.cross_entropy(outputs["condition"], targets["condition"])
    return tread * 3.5 + health * 0.7 + life * 0.7 + wear * 0.5 + condition * 0.4


def _metrics(outputs_list: list[dict[str, torch.Tensor]], targets_list: list[dict[str, torch.Tensor]], loss_value: float) -> dict[str, Any]:
    outputs = {
        key: torch.cat([item[key].detach().cpu() for item in outputs_list], dim=0)
        for key in outputs_list[0]
    }
    targets = {
        key: torch.cat([item[key].detach().cpu() for item in targets_list], dim=0)
        for key in targets_list[0]
    }
    condition_pred = outputs["condition"].argmax(dim=1)
    wear_pred = outputs["wear_pattern"].argmax(dim=1)
    tread_abs_error_mm = torch.abs(outputs["tread_depths"] - targets["tread_depths"]) * TREAD_MAX_MM
    avg_tread_abs_error_mm = (
        torch.abs(outputs["tread_depths"].mean(dim=1) - targets["tread_depths"].mean(dim=1))
        * TREAD_MAX_MM
    )
    return {
        "loss": round(float(loss_value), 6),
        "condition_accuracy": round(float((condition_pred == targets["condition"]).float().mean().item()), 4),
        "wear_accuracy": round(float((wear_pred == targets["wear_pattern"]).float().mean().item()), 4),
        "tread_mae_mm": round(float(torch.mean(tread_abs_error_mm).item()), 4),
        "avg_tread_mae_mm": round(float(torch.mean(avg_tread_abs_error_mm).item()), 4),
        "tread_within_1mm": round(float((tread_abs_error_mm <= 1.0).float().mean().item()), 4),
        "health_mae": round(float(torch.mean(torch.abs(outputs["health_score"] - targets["health_score"])).item() * 10.0), 4),
        "remaining_life_mae_km": round(float(torch.mean(torch.abs(outputs["remaining_life"] - targets["remaining_life"])).item() * MAX_REMAINING_KM), 2),
        "samples": int(targets["condition"].numel()),
    }


def _acceptance_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Return deployment gate status for the runtime tread-depth contract."""
    checks = {
        "tread_mae_mm": float(metrics.get("tread_mae_mm", float("inf"))) <= MAX_TEST_TREAD_MAE_MM,
        "avg_tread_mae_mm": float(metrics.get("avg_tread_mae_mm", float("inf"))) <= MAX_TEST_AVG_TREAD_MAE_MM,
        "tread_within_1mm": float(metrics.get("tread_within_1mm", 0.0)) >= MIN_TEST_TREAD_WITHIN_1MM,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "max_tread_mae_mm": MAX_TEST_TREAD_MAE_MM,
            "max_avg_tread_mae_mm": MAX_TEST_AVG_TREAD_MAE_MM,
            "min_tread_within_1mm": MIN_TEST_TREAD_WITHIN_1MM,
        },
    }


def _monitor_value(metrics: dict[str, Any]) -> float:
    """Lower is better; align checkpointing with the runtime ±1 mm gate."""
    tread_mae = float(metrics.get("tread_mae_mm", float("inf")))
    avg_mae = float(metrics.get("avg_tread_mae_mm", float("inf")))
    within_gap = max(0.0, MIN_TEST_TREAD_WITHIN_1MM - float(metrics.get("tread_within_1mm", 0.0)))
    return tread_mae + avg_mae * 0.35 + within_gap * 2.0


def _quarantine_rejected_checkpoint(config: FreshHybridConfig) -> None:
    """Move failed runtime checkpoints out of loadable paths."""
    rejected_dir = config.output_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    for checkpoint_name in ("model_best.pt", "model_last.pt"):
        checkpoint = config.output_dir / checkpoint_name
        if checkpoint.exists():
            destination = rejected_dir / checkpoint_name
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination = rejected_dir / f"{checkpoint.stem}_{timestamp}{checkpoint.suffix}"
            shutil.move(str(checkpoint), str(destination))


def _calibrated_outputs(
    outputs: dict[str, torch.Tensor],
    calibrator: IsotonicTreadCalibrator | None,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    if calibrator is None:
        return outputs
    calibrated_tread = apply_tread_calibration_array(
        outputs["tread_depths"].detach().cpu().numpy(),
        calibrator,
    )
    calibrated = dict(outputs)
    calibrated["tread_depths"] = torch.from_numpy(calibrated_tread).to(device)
    return calibrated


def _forward_with_symmetric_tta(
    model: HybridTireModel,
    inputs: dict[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    """Average original and horizontally flipped predictions."""
    outputs = model(inputs)
    flipped_inputs = {
        "image": torch.flip(inputs["image"], dims=[3]),
        "tread_sequence": inputs["tread_sequence"],
    }
    flipped_outputs = model(flipped_inputs)
    return {
        "tread_depths": 0.5
        * (
            outputs["tread_depths"]
            + torch.flip(flipped_outputs["tread_depths"], dims=[1])
        ),
        "health_score": 0.5 * (outputs["health_score"] + flipped_outputs["health_score"]),
        "remaining_life": 0.5 * (outputs["remaining_life"] + flipped_outputs["remaining_life"]),
        "wear_pattern": 0.5 * (outputs["wear_pattern"] + flipped_outputs["wear_pattern"]),
        "condition": 0.5 * (outputs["condition"] + flipped_outputs["condition"]),
    }


def evaluate(
    model: HybridTireModel,
    loader: DataLoader,
    device: torch.device,
    calibrator: IsotonicTreadCalibrator | None = None,
) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    outputs_list: list[dict[str, torch.Tensor]] = []
    targets_list: list[dict[str, torch.Tensor]] = []
    with torch.no_grad():
        for batch in loader:
            inputs, targets = _move_batch(batch, device)
            outputs = _forward_with_symmetric_tta(model, inputs)
            outputs_for_metrics = _calibrated_outputs(outputs, calibrator, device)
            loss = _loss(outputs_for_metrics, targets, model)
            losses.append(float(loss.item()))
            outputs_list.append(outputs_for_metrics)
            targets_list.append(targets)
    return _metrics(outputs_list, targets_list, float(np.mean(losses)))


def _collect_tread_predictions(
    model: HybridTireModel,
    loader: DataLoader,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            inputs, batch_targets = _move_batch(batch, device)
            outputs = _forward_with_symmetric_tta(model, inputs)
            predictions.append(outputs["tread_depths"].detach().cpu().numpy())
            targets.append(batch_targets["tread_depths"].detach().cpu().numpy())
    return np.concatenate(predictions, axis=0), np.concatenate(targets, axis=0)


def _autocast_enabled(device: torch.device) -> bool:
    return device.type == "cuda"


def _apply_mixup(
    inputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    device: torch.device,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    if np.random.rand() >= MIXUP_PROBABILITY or inputs["image"].shape[0] <= 1:
        return inputs, targets

    lam = float(np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA))
    rand_index = torch.randperm(inputs["image"].shape[0], device=device)

    mixed_inputs = dict(inputs)
    mixed_inputs["image"] = lam * inputs["image"] + (1.0 - lam) * inputs["image"][rand_index]
    if inputs["tread_sequence"].dtype.is_floating_point:
        mixed_inputs["tread_sequence"] = (
            lam * inputs["tread_sequence"]
            + (1.0 - lam) * inputs["tread_sequence"][rand_index]
        )

    mixed_targets = dict(targets)
    for key, value in targets.items():
        if value.dtype.is_floating_point:
            mixed_targets[key] = lam * value + (1.0 - lam) * value[rand_index]
    return mixed_inputs, mixed_targets


def train_epoch(
    model: HybridTireModel,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scaler: Any,
    device: torch.device,
    grad_accum_steps: int,
) -> float:
    model.train()
    losses: list[float] = []
    optimizer.zero_grad(set_to_none=True)
    use_amp = _autocast_enabled(device)
    for step, batch in enumerate(loader, start=1):
        inputs, targets = _move_batch(batch, device)
        inputs, targets = _apply_mixup(inputs, targets, device)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            outputs = model(inputs)
            loss = _loss(outputs, targets, model) / max(1, grad_accum_steps)
        scaler.scale(loss).backward()
        if step % grad_accum_steps == 0 or step == len(loader):
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
        losses.append(float(loss.item()) * max(1, grad_accum_steps))
    return float(np.mean(losses))


def _save_checkpoint(
    model: HybridTireModel,
    path: Path,
    config: FreshHybridConfig,
    metrics: dict[str, Any],
    epoch: int,
    stage: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "model_version": HYBRID_MODEL_VERSION,
            "epoch": epoch,
            "stage": stage,
            "metrics": metrics,
            "config": {key: str(value) if isinstance(value, Path) else value for key, value in asdict(config).items()},
        },
        path,
    )


def _config_payload(config: FreshHybridConfig) -> dict[str, Any]:
    return {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(config).items()
    }


def _relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _best_loss_from_checkpoint(checkpoint_path: Path) -> float:
    """Read the monitored tread MAE from an existing checkpoint when resuming."""
    if not checkpoint_path.exists():
        return float("inf")
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
    except Exception:
        return float("inf")
    metrics = checkpoint.get("metrics", {})
    try:
        return _monitor_value(metrics)
    except (TypeError, ValueError):
        return float("inf")


def _resolve_checkpoint_path(path_text: str | None, project_root: Path) -> Path | None:
    if not path_text:
        return None
    checkpoint_path = Path(path_text)
    if not checkpoint_path.is_absolute():
        checkpoint_path = project_root / checkpoint_path
    return checkpoint_path


def _write_runtime_registry(
    config: FreshHybridConfig,
    metadata: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    """Refresh top-level runtime metadata so the project reports the hybrid model."""
    registry = {
        "generated_at": metadata["generated_at"],
        "runtime_model": "hybrid_torch",
        "model_version": metadata["model_version"],
        "architecture": metadata["architecture"],
        "dataset": metadata["dataset"],
        "tread_sequence_source": metadata.get("tread_sequence_source"),
        "label_leakage_prevented": metadata.get("label_leakage_prevented"),
        "calibration": metadata.get("calibration"),
        "inference_strategy": metadata.get("inference_strategy"),
        "training_config": _config_payload(config),
        "models": {
            "hybrid_torch": {
                "best_weights": _relative_to_project(config.output_dir / "model_best.pt", config.project_root),
                "last_weights": _relative_to_project(config.output_dir / "model_last.pt", config.project_root),
                "metadata": _relative_to_project(config.output_dir / "metadata.json", config.project_root),
                "history": _relative_to_project(config.output_dir / "history.json", config.project_root),
                "metrics": _relative_to_project(config.output_dir / "metrics.json", config.project_root),
                "validation_metrics": metrics["validation"],
                "test_metrics": metrics["test"],
            }
        },
    }
    config.saved_models_dir.mkdir(parents=True, exist_ok=True)
    (config.saved_models_dir / "model_registry.json").write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )

    top_level_metadata = {
        "model_type": "HybridTireModel",
        "model_version": metadata["model_version"],
        "architecture": metadata["architecture"],
        "condition_labels": metadata["condition_labels"],
        "wear_labels": metadata["wear_labels"],
        "dataset": metadata["dataset"],
        "tread_sequence_source": metadata.get("tread_sequence_source"),
        "label_leakage_prevented": metadata.get("label_leakage_prevented"),
        "calibration": metadata.get("calibration"),
        "inference_strategy": metadata.get("inference_strategy"),
        "checkpoint": metadata["checkpoint"],
        "device_used_for_training": metadata["device"],
        "best_validation_loss": metadata["best_validation_loss"],
        "validation_metrics": metrics["validation"],
        "test_metrics": metrics["test"],
    }
    (config.saved_models_dir / "model_metadata.json").write_text(
        json.dumps(top_level_metadata, indent=2),
        encoding="utf-8",
    )


def _train_stage(
    model: HybridTireModel,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: FreshHybridConfig,
    device: torch.device,
    epochs: int,
    learning_rate: float,
    stage: str,
    history: list[dict[str, Any]],
    best_loss: float,
    early_stopping: bool = True,
) -> float:
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=learning_rate,
        weight_decay=config.weight_decay,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    stale_epochs = 0

    for epoch in range(1, epochs + 1):
        started = time.time()
        train_loss = train_epoch(
            model,
            train_loader,
            optimizer,
            scaler,
            device,
            grad_accum_steps=config.grad_accum_steps,
        )
        val_metrics = evaluate(model, val_loader, device)
        row = {
            "stage": stage,
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "validation": val_metrics,
            "elapsed_seconds": round(time.time() - started, 1),
            "trainable_parameters": count_trainable_parameters(model),
        }
        history.append(row)
        logger.info(
            "%s epoch %d/%d train_loss=%.4f val_loss=%.4f val_condition_acc=%.3f val_wear_acc=%.3f",
            stage,
            epoch,
            epochs,
            train_loss,
            val_metrics["loss"],
            val_metrics["condition_accuracy"],
            val_metrics["wear_accuracy"],
        )
        _save_checkpoint(model, config.output_dir / "model_last.pt", config, val_metrics, epoch, stage)

        monitor_value = _monitor_value(val_metrics)
        best_checkpoint_path = config.output_dir / "model_best.pt"
        if not best_checkpoint_path.exists() or monitor_value < best_loss:
            best_loss = monitor_value
            stale_epochs = 0
            _save_checkpoint(model, best_checkpoint_path, config, val_metrics, epoch, stage)
        else:
            stale_epochs += 1
            if early_stopping and stale_epochs >= config.patience:
                logger.info("%s early stopping after %d stale epochs", stage, stale_epochs)
                break
    return best_loss


def train_fresh_hybrid(config: FreshHybridConfig) -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if config.archive_old:
        archive_dir = archive_legacy_artifacts(config.saved_models_dir, project_root=config.project_root)
        if archive_dir is not None:
            logger.info("Archived old model artifacts at %s", archive_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if config.pretrained_required:
        logger.info("Pretrained EfficientNetV2-B0 and ViT-B/16 weights are required for this run.")
    logger.info("Using device: %s", device)

    train_dataset = HybridTireDataset(config.split_root / "train", sequence_source=config.tread_sequence_source)
    val_dataset = HybridTireDataset(config.split_root / "validation", sequence_source=config.tread_sequence_source)
    test_dataset = HybridTireDataset(config.split_root / "test", sequence_source=config.tread_sequence_source)
    train_loader = _make_loader(train_dataset, config.batch_size, True, config.num_workers)
    val_loader = _make_loader(val_dataset, config.batch_size, False, config.num_workers)
    test_loader = _make_loader(test_dataset, config.batch_size, False, config.num_workers)

    model = HybridTireModel(pretrained=config.pretrained_required).to(device)
    if config.resume_checkpoint:
        checkpoint_path = _resolve_checkpoint_path(config.resume_checkpoint, config.project_root)
        if checkpoint_path is None:
            raise ValueError("resume_checkpoint could not be resolved")
        checkpoint = torch.load(checkpoint_path, map_location=device)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        model.load_state_dict(state_dict)
        logger.info("Resumed hybrid weights from %s", checkpoint_path)
    model.set_encoder_trainable(False)
    history: list[dict[str, Any]] = []
    best_loss = float("inf")
    resume_checkpoint_path = _resolve_checkpoint_path(config.resume_checkpoint, config.project_root)
    if resume_checkpoint_path is not None:
        best_loss = _best_loss_from_checkpoint(resume_checkpoint_path)

    best_loss = _train_stage(
        model,
        train_loader,
        val_loader,
        config,
        device,
        config.stage1_epochs,
        config.learning_rate,
        "stage1_frozen_encoders",
        history,
        best_loss,
    )

    stage2_status = "not_requested"
    if config.stage2_epochs > 0:
        stage2_status = "completed"
        try:
            model.unfreeze_last_blocks()
            stage2_loader = _make_loader(train_dataset, config.stage2_batch_size, True, config.num_workers)
            best_loss = _train_stage(
                model,
                stage2_loader,
                val_loader,
                config,
                device,
                config.stage2_epochs,
                config.fine_tune_learning_rate,
                "stage2_last_blocks",
                history,
                float("inf"),
                early_stopping=False,
            )
        except RuntimeError as exc:
            if "out of memory" not in str(exc).lower():
                raise
            stage2_status = f"skipped_oom: {exc}"
            logger.warning("Stage 2 skipped because of CUDA OOM: %s", exc)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    best_checkpoint_path = config.output_dir / "model_best.pt"
    if not best_checkpoint_path.exists():
        best_checkpoint_path = config.output_dir / "model_last.pt"
        logger.warning("Best checkpoint missing; falling back to %s", best_checkpoint_path)
    best_checkpoint = torch.load(best_checkpoint_path, map_location=device)
    model.load_state_dict(best_checkpoint["model_state_dict"])
    model.to(device)
    val_tread_predictions, val_tread_targets = _collect_tread_predictions(model, val_loader, device)
    tread_calibrator = fit_isotonic_tread_calibrator(val_tread_predictions, val_tread_targets)
    calibration_path = config.output_dir / "tread_calibration.json"
    saved_calibration_path = save_tread_calibrator(tread_calibrator, calibration_path)
    test_metrics = evaluate(model, test_loader, device, calibrator=tread_calibrator)
    val_metrics = evaluate(model, val_loader, device, calibrator=tread_calibrator)

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": HYBRID_MODEL_VERSION,
        "architecture": {
            "cnn": "EfficientNetV2-B0",
            "transformer": "ViT-B/16",
            "rnn": "BiLSTM + TCN",
            "fusion": "Cross-Modal Attention + Deep Dense Fusion Network",
            "ann": "Multi-task Prediction Heads",
        },
        "condition_labels": CONDITION_LABELS,
        "wear_labels": WEAR_LABELS,
        "dataset": split_summary(config.split_root),
        "tread_sequence_source": config.tread_sequence_source,
        "label_leakage_prevented": config.tread_sequence_source.strip().lower()
        not in {"label", "labels", "oracle", "ground_truth"},
        "stage2_status": stage2_status,
        "device": str(device),
        "best_validation_loss": val_metrics["loss"],
        "best_validation_tread_mae_mm": val_metrics["tread_mae_mm"],
        "checkpoint": str((config.output_dir / "model_best.pt").relative_to(config.project_root)),
        "calibration": (
            str(calibration_path.relative_to(config.project_root))
            if saved_calibration_path is not None
            else None
        ),
        "inference_strategy": {
            "test_time_augmentation": True,
            "symmetric_horizontal_flip": True,
            "tread_calibration": saved_calibration_path is not None,
            "mixup": {
                "probability": MIXUP_PROBABILITY,
                "alpha": MIXUP_ALPHA,
            },
        },
    }
    metrics = {
        "validation": val_metrics,
        "test": test_metrics,
    }
    acceptance = _acceptance_gate(test_metrics)
    metadata["acceptance"] = acceptance
    metrics["acceptance"] = acceptance
    (config.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (config.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (config.output_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    if not acceptance["passed"]:
        _quarantine_rejected_checkpoint(config)
        raise RuntimeError(
            "Hybrid model failed tread-depth acceptance gate: "
            f"{json.dumps(acceptance, sort_keys=True)}"
        )
    _write_runtime_registry(config, metadata, metrics)

    logger.info("Fresh hybrid training complete. Test metrics: %s", test_metrics)
    return {"metadata": metadata, "metrics": metrics, "history": history}


def config_from_args(args: Any, project_root: Path) -> FreshHybridConfig:
    return FreshHybridConfig(
        project_root=project_root,
        stage1_epochs=int(getattr(args, "hybrid_stage1_epochs", 8)),
        stage2_epochs=int(getattr(args, "hybrid_stage2_epochs", 12)),
        batch_size=int(getattr(args, "hybrid_batch_size", 2)),
        stage2_batch_size=int(getattr(args, "hybrid_stage2_batch_size", 1)),
        grad_accum_steps=int(getattr(args, "hybrid_grad_accum_steps", 8)),
        learning_rate=float(getattr(args, "hybrid_learning_rate", 1e-4)),
        fine_tune_learning_rate=float(getattr(args, "hybrid_fine_tune_learning_rate", 1e-5)),
        weight_decay=float(getattr(args, "weight_decay", 1e-3)),
        patience=int(getattr(args, "patience", 3)),
        archive_old=bool(getattr(args, "archive_old", False)),
        pretrained_required=bool(getattr(args, "full_train", False) or getattr(args, "hybrid_pretrained", False)),
        tread_sequence_source=str(getattr(args, "hybrid_sequence_source", RUNTIME_TREAD_SEQUENCE_SOURCE)),
        resume_checkpoint=getattr(args, "hybrid_resume_checkpoint", None),
    )


def train_from_cli_args(args: Any, project_root: Path) -> dict[str, Any]:
    return train_fresh_hybrid(config_from_args(args, project_root))
