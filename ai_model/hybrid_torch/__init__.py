"""Fresh PyTorch hybrid model package for Smart Tire Analyzer."""

from ai_model.hybrid_torch.constants import (
    CONDITION_LABELS,
    HYBRID_MODEL_VERSION,
    WEAR_LABELS,
)


def __getattr__(name: str):
    if name == "HybridTireModel":
        from ai_model.hybrid_torch.model import HybridTireModel

        return HybridTireModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CONDITION_LABELS",
    "HYBRID_MODEL_VERSION",
    "HybridTireModel",
    "WEAR_LABELS",
]
