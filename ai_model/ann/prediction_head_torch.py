"""
ANN Prediction Head (PyTorch) — Final prediction layers for Smart Tire Analyzer.
PyTorch equivalent of prediction_head.py for the inference pipeline.
"""

import torch
import torch.nn as nn
from typing import Dict, Tuple

WEAR_CLASSES = 6
TREAD_MAX_MM = 12.0
HEALTH_SCORE_MAX = 10.0
MAX_REMAINING_KM = 80000.0


class TreadDepthHead(nn.Module):
    """
    Regression head for predicting all 4 individual tread depths.
    """

    def __init__(self, dropout_rate: float = 0.2):
        super().__init__()
        self.shared = nn.Sequential(
            nn.LazyLinear(256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(dropout_rate),
            nn.LazyLinear(128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
        )
        self.t1_out = nn.LazyLinear(1)
        self.t2_out = nn.LazyLinear(1)
        self.t3_out = nn.LazyLinear(1)
        self.t4_out = nn.LazyLinear(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        shared = self.shared(x)
        t1 = torch.sigmoid(self.t1_out(shared))
        t2 = torch.sigmoid(self.t2_out(shared))
        t3 = torch.sigmoid(self.t3_out(shared))
        t4 = torch.sigmoid(self.t4_out(shared))
        return torch.cat([t1, t2, t3, t4], dim=-1)


class HealthScoreHead(nn.Module):
    """
    Regression head for tire health score (0–10).
    """

    def __init__(self, dropout_rate: float = 0.3):
        super().__init__()
        self.d1 = nn.LazyLinear(128)
        self.bn1 = nn.BatchNorm1d(128)
        self.drop = nn.Dropout(dropout_rate)
        self.d2 = nn.LazyLinear(64)
        self.out = nn.LazyLinear(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.d1(x)
        x = self.bn1(x)
        x = self.drop(x)
        x = self.d2(x)
        return torch.sigmoid(self.out(x))

    def monte_carlo_estimate(
        self, x: torch.Tensor, n_samples: int = 20
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        self.train()
        predictions = torch.stack([self.forward(x) for _ in range(n_samples)], dim=0)
        self.eval()
        mean = predictions.mean(dim=0)
        std = predictions.std(dim=0)
        return mean, std


class RemainingLifeHead(nn.Module):
    """
    Regression head for remaining tire life in km.
    """

    def __init__(self, dropout_rate: float = 0.2):
        super().__init__()
        self.d1 = nn.LazyLinear(128)
        self.bn = nn.BatchNorm1d(128)
        self.drop = nn.Dropout(dropout_rate)
        self.d2 = nn.LazyLinear(64)
        self.out = nn.LazyLinear(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.d1(x)
        x = self.bn(x)
        x = self.drop(x)
        x = self.d2(x)
        return torch.sigmoid(self.out(x))


class WearPatternHead(nn.Module):
    """
    Classification head for wear pattern detection.
    6 classes: center, edge, patchy, uniform, one-side, cupping.
    """

    def __init__(self, num_classes: int = WEAR_CLASSES, dropout_rate: float = 0.3):
        super().__init__()
        self.num_classes = num_classes
        self.d1 = nn.LazyLinear(256)
        self.bn1 = nn.BatchNorm1d(256)
        self.drop1 = nn.Dropout(dropout_rate)
        self.d2 = nn.LazyLinear(128)
        self.bn2 = nn.BatchNorm1d(128)
        self.drop2 = nn.Dropout(dropout_rate)
        self.out = nn.LazyLinear(num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.d1(x)
        x = self.bn1(x)
        x = self.drop1(x)
        x = self.d2(x)
        x = self.bn2(x)
        x = self.drop2(x)
        return torch.softmax(self.out(x), dim=-1)


class PredictionHead(nn.Module):
    """
    Complete ANN prediction head with 4 output branches.
    """

    def __init__(self, fused_dim: int = 512, dropout_rate: float = 0.25):
        super().__init__()
        self.shared = nn.Sequential(
            nn.LazyLinear(512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(dropout_rate),
            nn.LazyLinear(256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
        )
        self.tread_head = TreadDepthHead(dropout_rate=dropout_rate)
        self.health_head = HealthScoreHead(dropout_rate=dropout_rate)
        self.life_head = RemainingLifeHead(dropout_rate=dropout_rate)
        self.wear_head = WearPatternHead(dropout_rate=dropout_rate)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        shared = self.shared(x)
        return {
            "tread_depths": self.tread_head(shared),
            "health_score": self.health_head(shared),
            "remaining_life": self.life_head(shared),
            "wear_pattern": self.wear_head(shared),
        }
