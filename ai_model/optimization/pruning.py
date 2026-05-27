"""
Model pruning for smaller, faster Smart Tire models.
Uses tensorflow-model-optimization for structured or unstructured pruning.
"""

from __future__ import annotations

# pyright: reportMissingTypeStubs=false

import logging
from typing import Any, TypedDict, TypeAlias, cast

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

KerasModel: TypeAlias = Any
PruningCallback: TypeAlias = Any
FloatArray: TypeAlias = npt.NDArray[np.float64]


class LayerStat(TypedDict):
    layer: str
    param: str
    total: int
    zero: int
    sparsity: float


class SparsityReport(TypedDict):
    overall_sparsity: float
    total_weights: int
    zero_weights: int
    non_zero_weights: int
    layer_stats: list[LayerStat]


def _load_tfmot() -> Any | None:
    """Import tensorflow-model-optimization lazily."""
    try:
        import tensorflow_model_optimization as tfmot

        return cast(Any, tfmot)
    except ImportError:
        logger.error(
            "tensorflow-model-optimization not installed.\n"
            "Install with: pip install tensorflow-model-optimization"
        )
        return None


class ModelPruner:
    """
    Implements magnitude-based weight pruning for the Smart Tire model.

    Pruning makes weights sparse, enabling:
    - better compression
    - faster inference on supporting hardware
    - smaller deployment footprint

    Two-phase process:
    1. Prune during fine-tuning with a gradual sparsity schedule
    2. Strip pruning wrappers and export the clean sparse model
    """

    def __init__(self, model: KerasModel) -> None:
        self.model: KerasModel = model
        self._pruned_model: KerasModel | None = None
        self._pruning_enabled = False

    def apply_pruning(
        self,
        target_sparsity: float = 0.50,
        begin_step: int = 0,
        end_step: int = 500,
        frequency: int = 50,
    ) -> KerasModel:
        """
        Wrap dense layers with pruning callbacks.

        Args:
            target_sparsity: Final fraction of weights to zero out
            begin_step: Training step where pruning begins
            end_step: Training step where target sparsity is reached
            frequency: Pruning update frequency in steps

        Returns:
            Model with pruning wrappers applied
        """
        tfmot = _load_tfmot()
        if tfmot is None:
            self._pruning_enabled = False
            return self.model

        tfmot_keras: Any = tfmot.sparsity.keras
        pruning_schedule: Any = tfmot_keras.PolynomialDecay(
            initial_sparsity=0.20,
            final_sparsity=target_sparsity,
            begin_step=begin_step,
            end_step=end_step,
            frequency=frequency,
        )
        try:
            pruned_model: Any = tfmot_keras.prune_low_magnitude(
                self.model,
                pruning_schedule=pruning_schedule,
            )
        except Exception as exc:
            self._pruned_model = None
            self._pruning_enabled = False
            logger.error(
                "Pruning could not be applied in the current TensorFlow/TFMOT environment: %s",
                exc,
            )
            return self.model

        self._pruned_model = pruned_model
        self._pruning_enabled = True

        logger.info(
            "Pruning applied: %.0f%% target sparsity, steps %d-%d",
            target_sparsity * 100.0,
            begin_step,
            end_step,
        )
        return self._pruned_model

    def get_pruning_callback(self) -> list[PruningCallback]:
        """Return pruning callbacks to pass to model.fit()."""
        if not self._pruning_enabled:
            return []

        tfmot = _load_tfmot()
        if tfmot is None:
            return []

        return [tfmot.sparsity.keras.UpdatePruningStep()]

    def strip_pruning(self, pruned_model: KerasModel | None = None) -> KerasModel:
        """
        Strip pruning wrappers after training.

        The returned model keeps zeroed weights but removes pruning-specific
        training wrappers.
        """
        model_to_strip: Any = pruned_model or self._pruned_model or self.model
        if not self._pruning_enabled:
            return model_to_strip

        tfmot = _load_tfmot()
        if tfmot is None:
            return model_to_strip

        try:
            stripped_model: Any = tfmot.sparsity.keras.strip_pruning(model_to_strip)
            logger.info("Pruning wrappers stripped; clean sparse model ready")
            return stripped_model
        except Exception as exc:
            logger.error("Pruning wrappers could not be stripped: %s", exc)
            return model_to_strip

    def measure_sparsity(self, model: KerasModel | None = None) -> SparsityReport:
        """
        Measure actual weight sparsity of the model.

        Returns:
            Overall and per-layer sparsity statistics
        """
        active_model: Any = model or self._pruned_model or self.model
        layer_stats: list[LayerStat] = []
        total_weights = 0
        zero_weights = 0

        for layer in cast(list[Any], active_model.layers):
            layer_name = str(getattr(layer, "name", "unknown_layer"))
            for weight in cast(list[Any], layer.weights):
                weight_name = str(getattr(weight, "name", "weight"))
                weight_array: FloatArray = np.asarray(weight.numpy(), dtype=np.float64)
                n_total = int(weight_array.size)
                n_zero = int(np.sum(np.abs(weight_array) < 1e-7))
                sparsity = n_zero / max(n_total, 1)
                total_weights += n_total
                zero_weights += n_zero

                if n_total > 100:
                    layer_stats.append(
                        {
                            "layer": layer_name,
                            "param": weight_name.split("/")[-1],
                            "total": n_total,
                            "zero": n_zero,
                            "sparsity": round(sparsity, 4),
                        }
                    )

        overall_sparsity = zero_weights / max(total_weights, 1)
        return {
            "overall_sparsity": round(overall_sparsity, 4),
            "total_weights": total_weights,
            "zero_weights": zero_weights,
            "non_zero_weights": total_weights - zero_weights,
            "layer_stats": layer_stats,
        }
