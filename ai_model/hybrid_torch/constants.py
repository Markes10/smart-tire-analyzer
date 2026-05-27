"""Shared constants for the fresh PyTorch hybrid model."""

from __future__ import annotations

HYBRID_MODEL_VERSION = "pytorch_hybrid:efficientnetv2_b0_vit_b16_bilstm_tcn_attention_calibrated"

IMAGE_SIZE = 224
TREAD_MAX_MM = 12.0
HEALTH_MAX = 10.0
MAX_REMAINING_KM = 80_000.0
TREAD_SEQUENCE_DIM = 7

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

WEAR_LABELS = [
    "center_wear",
    "edge_wear",
    "patchy_wear",
    "uniform_wear",
    "one_side_wear",
    "cupping_wear",
]

WEAR_ALIASES = {
    "center_wear": "center_wear",
    "edge_wear": "edge_wear",
    "patchy_wear": "patchy_wear",
    "patch_wear": "patchy_wear",
    "uniform_wear": "uniform_wear",
    "even": "uniform_wear",
    "even_wear": "uniform_wear",
    "one_side_wear": "one_side_wear",
    "one_sided_wear": "one_side_wear",
    "cupping_wear": "cupping_wear",
    "cupping": "cupping_wear",
    "uneven_wear": "patchy_wear",
    "critical_wear": "patchy_wear",
}

CONDITION_LABELS = ["safe", "moderate", "replace"]
