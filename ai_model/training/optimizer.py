"""
Optimizer and learning-rate schedules for Smart Tire Analyzer training.
Implements AdamW with linear warmup + cosine decay.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, TypeAlias, cast

import tensorflow as tf

StepInput: TypeAlias = tf.Tensor | int | float
ScheduleConfig: TypeAlias = dict[str, float | int]
LearningRateLike: TypeAlias = float | tf.keras.optimizers.schedules.LearningRateSchedule
OptimizerType: TypeAlias = Any

TF: Any = tf
KerasAPI: Any = importlib.import_module("tensorflow.keras")
KerasOptimizers: Any = KerasAPI.optimizers
MixedPrecisionAPI: Any = KerasAPI.mixed_precision


def _to_float_tensor(value: object) -> tf.Tensor:
    """Convert scalars or tensors to float32 tensors through a narrow Any boundary."""
    return cast(tf.Tensor, TF.cast(value, tf.float32))


class WarmupCosineDecaySchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
    """
    Linear warmup followed by cosine decay.
    - Warmup: LR increases linearly from 0 to peak_lr over warmup_steps
    - Decay: LR decays following a cosine curve from peak_lr to min_lr
    """

    def __init__(
        self,
        peak_lr: float = 1e-4,
        warmup_steps: int = 500,
        total_steps: int = 5000,
        min_lr: float = 1e-7,
    ) -> None:
        super().__init__()
        self.peak_lr = peak_lr
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr

    def __call__(self, step: StepInput) -> tf.Tensor:
        step_tensor = _to_float_tensor(step)
        warmup = _to_float_tensor(max(self.warmup_steps, 1))
        total = _to_float_tensor(max(self.total_steps, self.warmup_steps + 1))
        peak = _to_float_tensor(self.peak_lr)
        min_lr = _to_float_tensor(self.min_lr)

        warmup_lr = peak * step_tensor / warmup

        decay_steps = cast(tf.Tensor, TF.maximum(total - warmup, _to_float_tensor(1.0)))
        progress = (step_tensor - warmup) / decay_steps
        cosine_lr = min_lr + 0.5 * (peak - min_lr) * (1.0 + TF.cos(math.pi * progress))

        return cast(tf.Tensor, TF.where(step_tensor < warmup, warmup_lr, cosine_lr))

    def get_config(self) -> ScheduleConfig:
        return {
            "peak_lr": self.peak_lr,
            "warmup_steps": self.warmup_steps,
            "total_steps": self.total_steps,
            "min_lr": self.min_lr,
        }


class CyclicLRSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
    """
    Cyclic learning rate (CLR) for continuous learning and retraining.
    Helps escape local minima during incremental fine-tuning.
    """

    def __init__(
        self,
        base_lr: float = 1e-6,
        max_lr: float = 1e-4,
        step_size: int = 500,
    ) -> None:
        super().__init__()
        self.base_lr = base_lr
        self.max_lr = max_lr
        self.step_size = step_size

    def __call__(self, step: StepInput) -> tf.Tensor:
        step_tensor = _to_float_tensor(step)
        step_size = _to_float_tensor(max(self.step_size, 1))
        cycle = cast(tf.Tensor, TF.floor(1.0 + step_tensor / (2.0 * step_size)))
        distance = step_tensor / step_size - 2.0 * cycle + 1.0
        x = cast(tf.Tensor, TF.abs(distance))
        scale = cast(tf.Tensor, TF.maximum(_to_float_tensor(0.0), 1.0 - x))
        base_lr = _to_float_tensor(self.base_lr)
        max_lr = _to_float_tensor(self.max_lr)
        return base_lr + (max_lr - base_lr) * scale

    def get_config(self) -> ScheduleConfig:
        return {
            "base_lr": self.base_lr,
            "max_lr": self.max_lr,
            "step_size": self.step_size,
        }


def build_warmup_schedule(
    peak_lr: float = 1e-4,
    warmup_steps: int = 500,
    total_steps: int = 5000,
) -> WarmupCosineDecaySchedule:
    return WarmupCosineDecaySchedule(
        peak_lr=peak_lr,
        warmup_steps=warmup_steps,
        total_steps=total_steps,
    )


def build_optimizer(
    lr_schedule: LearningRateLike,
    weight_decay: float = 1e-5,
    gradient_clip: float = 1.0,
    use_mixed_precision: bool = True,
) -> OptimizerType:
    """
    Build AdamW optimizer with optional gradient scaling for mixed precision.

    Args:
        lr_schedule: learning-rate schedule or scalar
        weight_decay: L2 regularization strength
        gradient_clip: global norm clip value
        use_mixed_precision: wrap in LossScaleOptimizer for float16

    Returns:
        Configured optimizer
    """
    optimizer: Any = KerasOptimizers.AdamW(
        learning_rate=lr_schedule,
        weight_decay=weight_decay,
        clipnorm=gradient_clip,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-8,
    )

    if use_mixed_precision:
        optimizer = MixedPrecisionAPI.LossScaleOptimizer(optimizer)

    return optimizer
