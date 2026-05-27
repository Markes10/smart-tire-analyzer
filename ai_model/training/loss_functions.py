"""
Custom loss functions for multi-task tire analysis.
Combines regression and classification losses with task weighting.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeAlias, cast

import tensorflow as tf

TensorMap: TypeAlias = Mapping[str, tf.Tensor]
ConfigDict: TypeAlias = dict[str, float | str]

TF: Any = tf
KerasLosses: Any = tf.keras.losses


def _require_tensor(mapping: TensorMap, key: str) -> tf.Tensor:
    """Fetch a required tensor from a mapping and fail clearly if it is missing."""
    if key not in mapping:
        raise KeyError(f"Missing required loss key: {key}")
    return mapping[key]


class SmartTireLoss:
    """
    Multi-task loss combining:
    1. Tread depth loss - Huber regression
    2. Health score loss - MSE regression
    3. Remaining life loss - Huber regression
    4. Wear pattern loss - focal cross-entropy
    """

    def __init__(
        self,
        w_tread: float = 1.5,
        w_health: float = 1.0,
        w_life: float = 1.0,
        w_wear: float = 0.8,
        focal_gamma: float = 2.0,
        huber_delta: float = 1.0,
        name: str = "smart_tire_loss",
    ) -> None:
        self.name = name
        self.w_tread = w_tread
        self.w_health = w_health
        self.w_life = w_life
        self.w_wear = w_wear
        self.huber: Any = KerasLosses.Huber(delta=huber_delta)
        self.mse: Any = KerasLosses.MeanSquaredError()
        self.focal_gamma = focal_gamma

    def __call__(self, y_true: TensorMap, y_pred: TensorMap) -> tf.Tensor:
        return self.call(y_true, y_pred)

    def call(self, y_true: TensorMap, y_pred: TensorMap) -> tf.Tensor:
        """
        Args:
            y_true: {
                "tread_depths": (batch, 4) normalized,
                "health_score": (batch, 1) normalized,
                "remaining_life": (batch, 1) normalized,
                "wear_pattern": (batch,) integer class labels,
            }
            y_pred: same keys from model output
        """
        loss_tread = cast(
            tf.Tensor,
            self.huber(
                _require_tensor(y_true, "tread_depths"),
                _require_tensor(y_pred, "tread_depths"),
            ),
        )
        loss_health = cast(
            tf.Tensor,
            self.mse(
                _require_tensor(y_true, "health_score"),
                _require_tensor(y_pred, "health_score"),
            ),
        )
        loss_life = cast(
            tf.Tensor,
            self.huber(
                _require_tensor(y_true, "remaining_life"),
                _require_tensor(y_pred, "remaining_life"),
            ),
        )
        loss_wear = self._focal_crossentropy(
            _require_tensor(y_true, "wear_pattern"),
            _require_tensor(y_pred, "wear_pattern"),
        )

        total = (
            self.w_tread * loss_tread
            + self.w_health * loss_health
            + self.w_life * loss_life
            + self.w_wear * loss_wear
        )
        return total

    def _focal_crossentropy(self, y_true: tf.Tensor, y_pred: tf.Tensor) -> tf.Tensor:
        """
        Focal loss for imbalanced wear pattern classes.
        Focuses training on hard-to-classify samples.
        """
        n_classes = y_pred.shape[-1]
        if n_classes is None:
            raise ValueError("wear_pattern predictions must have a known class dimension")

        y_true_oh = cast(
            tf.Tensor,
            TF.one_hot(TF.cast(y_true, tf.int32), n_classes),
        )
        clipped_pred = cast(
            tf.Tensor,
            TF.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7),
        )

        pt = cast(tf.Tensor, TF.reduce_sum(y_true_oh * clipped_pred, axis=-1))
        focal_weight = cast(tf.Tensor, TF.pow(1.0 - pt, self.focal_gamma))
        ce = cast(
            tf.Tensor,
            -TF.reduce_sum(y_true_oh * TF.math.log(clipped_pred), axis=-1),
        )
        return cast(tf.Tensor, TF.reduce_mean(focal_weight * ce))

    def get_config(self) -> ConfigDict:
        return {
            "name": self.name,
            "w_tread": self.w_tread,
            "w_health": self.w_health,
            "w_life": self.w_life,
            "w_wear": self.w_wear,
            "focal_gamma": self.focal_gamma,
        }


class TreadDepthLoss:
    """
    Specialized tread depth loss with asymmetric penalty.
    Under-prediction is penalized more heavily than over-prediction.
    """

    def __init__(self, under_weight: float = 2.0, name: str = "tread_depth_loss") -> None:
        self.name = name
        self.under_weight = under_weight

    def __call__(self, y_true: tf.Tensor, y_pred: tf.Tensor) -> tf.Tensor:
        return self.call(y_true, y_pred)

    def call(self, y_true: tf.Tensor, y_pred: tf.Tensor) -> tf.Tensor:
        error = y_true - y_pred
        under_penalty = cast(
            tf.Tensor,
            TF.where(error > 0, self.under_weight * error, error),
        )
        return cast(tf.Tensor, TF.reduce_mean(TF.square(under_penalty)))

    def get_config(self) -> ConfigDict:
        return {
            "name": self.name,
            "under_weight": self.under_weight,
        }
