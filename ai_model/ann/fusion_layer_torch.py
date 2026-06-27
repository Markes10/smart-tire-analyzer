"""
Feature Fusion Layer (PyTorch) — Combines CNN + ViT + RNN embeddings.
PyTorch equivalent of fusion_layer.py for the inference pipeline.
"""

import torch
import torch.nn as nn
from typing import List


class GatedFusion(nn.Module):
    """
    Gated multi-modal fusion using learned attention weights.
    Each modality's contribution is controlled by a soft gate —
    allowing the model to down-weight unreliable branches.
    """

    def __init__(self, output_dim: int = 512, num_modalities: int = 3):
        super().__init__()
        self.output_dim = output_dim
        self.num_modalities = num_modalities

        self.projections = nn.ModuleList([
            nn.Sequential(
                nn.LazyLinear(output_dim),
                nn.ReLU(),
                nn.LayerNorm(output_dim),
            )
            for _ in range(num_modalities)
        ])

        self.gate_input_proj = nn.LazyLinear(output_dim)
        self.gate_act = nn.ReLU()
        self.gate_dense = nn.LazyLinear(num_modalities)

        self.fusion_dense = nn.Sequential(
            nn.LazyLinear(output_dim),
            nn.ReLU(),
            nn.LayerNorm(output_dim),
        )
        self.fusion_drop = nn.Dropout(0.2)

    def forward(self, features: List[torch.Tensor]) -> torch.Tensor:
        assert len(features) == self.num_modalities

        projected = []
        for i, feat in enumerate(features):
            p = self.projections[i](feat)
            projected.append(p)

        stacked = torch.stack(projected, dim=1)

        concat_all = torch.cat(features, dim=-1)
        gate_ctx = self.gate_act(self.gate_input_proj(concat_all))
        gate_logits = self.gate_dense(gate_ctx)
        gate_weights = torch.softmax(gate_logits, dim=-1)
        gate_weights = gate_weights.unsqueeze(-1)

        fused = (stacked * gate_weights).sum(dim=1)

        fused = self.fusion_dense(fused)
        fused = self.fusion_drop(fused)
        return fused


class ConcatFusion(nn.Module):
    """
    Simple concatenation + dense projection fusion.
    Faster but less flexible than gated fusion.
    """

    def __init__(self, output_dim: int = 512, dropout_rate: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.LazyLinear(1024),
            nn.ReLU(),
            nn.BatchNorm1d(1024),
            nn.Dropout(dropout_rate),
            nn.LazyLinear(output_dim),
            nn.ReLU(),
            nn.BatchNorm1d(output_dim),
        )

    def forward(self, features: List[torch.Tensor]) -> torch.Tensor:
        x = torch.cat(features, dim=-1)
        return self.net(x)
