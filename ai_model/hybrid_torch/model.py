"""EfficientNetV2-B0 + ViT-B/16 + BiLSTM + dense fusion model."""

from __future__ import annotations

import platform
from typing import Any

import torch
import torch.nn as nn


_TORCHVISION_COMPAT_LIB = None


def _ensure_torchvision_optional_ops() -> None:
    """
    Some CPU-only Windows torch/torchvision installs miss the compiled NMS op
    schema, but torchvision still registers a fake implementation at import
    time. Defining the schema lets model imports and CPU-only tests proceed.
    """
    global _TORCHVISION_COMPAT_LIB
    if platform.system() != "Windows":
        return

    try:
        torch._C._dispatch_find_schema_or_throw("torchvision::nms", "")
        return
    except RuntimeError:
        pass

    try:
        _TORCHVISION_COMPAT_LIB = torch.library.Library("torchvision", "DEF")
        _TORCHVISION_COMPAT_LIB.define("nms(Tensor dets, Tensor scores, float iou_threshold) -> Tensor")
    except RuntimeError:
        pass


try:
    from torchvision.models import ViT_B_16_Weights, vit_b_16
except RuntimeError as exc:
    if platform.system() != "Windows" or "torchvision::nms" not in str(exc):
        raise
    _ensure_torchvision_optional_ops()
    from torchvision.models import ViT_B_16_Weights, vit_b_16

from ai_model.hybrid_torch.constants import (
    CONDITION_LABELS,
    TREAD_SEQUENCE_DIM,
    WEAR_LABELS,
)


class EfficientNetV2B0Branch(nn.Module):
    """Local tread feature branch."""

    def __init__(self, pretrained: bool = True, feature_dim: int = 512) -> None:
        super().__init__()
        if platform.system() == "Windows":
            _ensure_torchvision_optional_ops()
        try:
            import timm
        except ImportError as exc:
            raise RuntimeError(
                "EfficientNetV2-B0 requires timm. Install dependencies with "
                "`pip install -r backend/requirements.txt`."
            ) from exc

        self.encoder = timm.create_model(
            "tf_efficientnetv2_b0.in1k",
            pretrained=pretrained,
            num_classes=0,
            global_pool="avg",
        )
        in_features = int(getattr(self.encoder, "num_features", 1280))
        self.projector = nn.Sequential(
            nn.Linear(in_features, feature_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(feature_dim),
            nn.Dropout(0.2),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        features = self.encoder(image)
        return self.projector(features)

    def unfreeze_last_blocks(self) -> None:
        """Fine-tune the final EfficientNetV2-B0 feature blocks."""
        for module_name in ("blocks", "conv_head", "bn2"):
            module = getattr(self.encoder, module_name, None)
            if module is None:
                continue
            modules = list(module.children()) if module_name == "blocks" else [module]
            if module_name == "blocks":
                modules = modules[-3:]
            for child in modules:
                for parameter in child.parameters():
                    parameter.requires_grad = True


class ViTB16Branch(nn.Module):
    """Global tread pattern branch."""

    def __init__(self, pretrained: bool = True, feature_dim: int = 512) -> None:
        super().__init__()
        weights = ViT_B_16_Weights.DEFAULT if pretrained else None
        self.encoder = vit_b_16(weights=weights)
        in_features = self.encoder.heads.head.in_features
        self.encoder.heads = nn.Identity()
        self.projector = nn.Sequential(
            nn.Linear(in_features, feature_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(feature_dim),
            nn.Dropout(0.2),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        features = self.encoder(image)
        return self.projector(features)


class BiLSTMBranch(nn.Module):
    """Sequential 4-position tread analysis branch."""

    def __init__(
        self,
        input_dim: int = TREAD_SEQUENCE_DIM,
        hidden_dim: int = 128,
        output_dim: int = 256,
    ) -> None:
        super().__init__()
        self.rnn = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.2,
        )
        self.projector = nn.Sequential(
            nn.Linear(hidden_dim * 2, output_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(output_dim),
            nn.Dropout(0.2),
        )

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        output, _ = self.rnn(sequence)
        pooled = output.mean(dim=1)
        return self.projector(pooled)


class SpatialTCNBranch(nn.Module):
    """Short-sequence convolutional branch for spatial tread-rib relationships."""

    def __init__(
        self,
        input_dim: int = TREAD_SEQUENCE_DIM,
        hidden_dim: int = 128,
        output_dim: int = 256,
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, kernel_size=3, padding=1),
            nn.GELU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=2, dilation=2),
            nn.GELU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=1),
            nn.GELU(),
        )
        self.projector = nn.Sequential(
            nn.Linear(hidden_dim, output_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(output_dim),
            nn.Dropout(0.2),
        )

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        features = self.net(sequence.transpose(1, 2))
        pooled = features.mean(dim=2)
        return self.projector(pooled)


class BiLSTMTCNBranch(nn.Module):
    """BiLSTM plus TCN sequence encoder for tiny four-position tread sequences."""

    def __init__(self, input_dim: int = TREAD_SEQUENCE_DIM, output_dim: int = 256) -> None:
        super().__init__()
        self.bilstm = BiLSTMBranch(input_dim=input_dim, output_dim=output_dim)
        self.tcn = SpatialTCNBranch(input_dim=input_dim, output_dim=output_dim)
        self.fusion = nn.Sequential(
            nn.Linear(output_dim * 2, output_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(output_dim),
            nn.Dropout(0.2),
        )

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        return self.fusion(torch.cat([self.bilstm(sequence), self.tcn(sequence)], dim=1))


class DeepDenseFusion(nn.Module):
    """Deep dense fusion network with cross-modal attention over feature tokens."""

    def __init__(self, output_dim: int = 512) -> None:
        super().__init__()
        self.cnn_proj = nn.Linear(512, output_dim)
        self.vit_proj = nn.Linear(512, output_dim)
        self.rnn_proj = nn.Linear(256, output_dim)
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=output_dim,
            num_heads=8,
            dropout=0.1,
            batch_first=True,
        )
        self.attention_norm = nn.LayerNorm(output_dim)
        self.gate = nn.Sequential(
            nn.Linear(output_dim * 3, output_dim),
            nn.ReLU(inplace=True),
            nn.Linear(output_dim, 3),
            nn.Softmax(dim=1),
        )
        self.fusion = nn.Sequential(
            nn.Linear(output_dim * 4, 1024),
            nn.ReLU(inplace=True),
            nn.LayerNorm(1024),
            nn.Dropout(0.4),
            nn.Linear(1024, output_dim),
            nn.ReLU(inplace=True),
            nn.LayerNorm(output_dim),
            nn.Dropout(0.4),
        )

    def forward(self, cnn: torch.Tensor, vit: torch.Tensor, rnn: torch.Tensor) -> torch.Tensor:
        projected = [self.cnn_proj(cnn), self.vit_proj(vit), self.rnn_proj(rnn)]
        tokens = torch.stack(projected, dim=1)
        attended, _ = self.cross_attention(tokens, tokens, tokens, need_weights=False)
        attended = self.attention_norm(tokens + attended)
        projected = [attended[:, index, :] for index in range(attended.shape[1])]
        concat = torch.cat(projected, dim=1)
        weights = self.gate(concat).unsqueeze(-1)
        stacked = torch.stack(projected, dim=1)
        gated = torch.sum(stacked * weights, dim=1)
        return self.fusion(torch.cat([concat, gated], dim=1))


class HybridTireModel(nn.Module):
    """Fresh multitask PyTorch hybrid tire model."""

    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        self.cnn = EfficientNetV2B0Branch(pretrained=pretrained)
        self.vit = ViTB16Branch(pretrained=pretrained)
        self.rnn = BiLSTMTCNBranch()
        self.fusion = DeepDenseFusion()
        self.loss_log_vars = nn.ParameterDict(
            {
                "tread": nn.Parameter(torch.zeros(())),
                "health": nn.Parameter(torch.zeros(())),
                "life": nn.Parameter(torch.zeros(())),
                "wear": nn.Parameter(torch.zeros(())),
                "condition": nn.Parameter(torch.zeros(())),
            }
        )
        self.tread_head = nn.Sequential(
            nn.Linear(1024, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 4),
            nn.Sigmoid(),
        )
        self.health_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
        self.life_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
        self.wear_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(256, len(WEAR_LABELS)),
        )
        self.condition_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(128, len(CONDITION_LABELS)),
        )

    def set_encoder_trainable(self, trainable: bool) -> None:
        for branch in (self.cnn.encoder, self.vit.encoder):
            for parameter in branch.parameters():
                parameter.requires_grad = trainable

    def unfreeze_last_blocks(self) -> None:
        self.set_encoder_trainable(False)
        self.cnn.unfreeze_last_blocks()
        for parameter in self.vit.encoder.encoder.layers[-4:].parameters():
            parameter.requires_grad = True

    def forward(self, inputs: dict[str, torch.Tensor] | torch.Tensor, tread_sequence: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        if isinstance(inputs, dict):
            image = inputs["image"]
            sequence = inputs["tread_sequence"]
        else:
            image = inputs
            if tread_sequence is None:
                raise ValueError("tread_sequence is required when inputs is a tensor")
            sequence = tread_sequence

        cnn_features = self.cnn(image)
        vit_features = self.vit(image)
        rnn_features = self.rnn(sequence)
        vision_fused = torch.cat([cnn_features, vit_features], dim=1)
        fused = self.fusion(cnn_features, vit_features, rnn_features)
        return {
            "tread_depths": self.tread_head(vision_fused),
            "health_score": self.health_head(fused),
            "remaining_life": self.life_head(fused),
            "wear_pattern": self.wear_head(fused),
            "condition": self.condition_head(fused),
        }


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def build_model_from_checkpoint(
    checkpoint: dict[str, Any],
    device: str | torch.device = "cpu",
) -> HybridTireModel:
    model = HybridTireModel(pretrained=False)
    state_dict = checkpoint.get("model_state_dict", checkpoint)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model
