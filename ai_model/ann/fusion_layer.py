"""
Feature Fusion Layer — Combines CNN + ViT + RNN embeddings.
The core integration point that merges multi-modal representations
into a single unified feature vector for final predictions.
"""

import tensorflow as tf
from tensorflow.keras import layers, Model
from typing import List, Optional, Tuple


class GatedFusionLayer(layers.Layer):
    """
    Gated multi-modal fusion using learned attention weights.
    Each modality's contribution is controlled by a soft gate —
    allowing the model to down-weight unreliable branches.
    """

    def __init__(self, output_dim: int = 512, num_modalities: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.output_dim = output_dim
        self.num_modalities = num_modalities

        # Per-modality projection to common space
        self.projections = [
            layers.Dense(output_dim, activation="relu", name=f"proj_{i}")
            for i in range(num_modalities)
        ]
        self.proj_norms = [
            layers.LayerNormalization(name=f"proj_ln_{i}")
            for i in range(num_modalities)
        ]

        # Gating network — produces soft weights over modalities
        self.gate_dense = layers.Dense(num_modalities, activation="softmax", name="gate_weights")
        self.gate_input = layers.Dense(output_dim, activation="relu", name="gate_input_proj")

        # Final fusion projection
        self.fusion_dense = layers.Dense(output_dim, activation="relu", name="fusion_proj")
        self.fusion_norm = layers.LayerNormalization(name="fusion_norm")
        self.fusion_drop = layers.Dropout(0.2, name="fusion_drop")

    def call(
        self,
        features: List[tf.Tensor],
        training: bool = False,
    ) -> tf.Tensor:
        """
        Args:
            features: List of [cnn_feat, vit_feat, rnn_feat], each (batch, dim)
        Returns:
            fused: (batch, output_dim)
        """
        assert len(features) == self.num_modalities

        # Project each modality to common space
        projected = []
        for i, (feat, proj, norm) in enumerate(zip(features, self.projections, self.proj_norms)):
            p = proj(feat)
            p = norm(p)
            projected.append(p)

        # Stack: (batch, num_modalities, output_dim)
        stacked = tf.stack(projected, axis=1)

        # Compute global context for gating
        concat_all = tf.concat(features, axis=-1)
        gate_ctx = self.gate_input(concat_all)
        gate_weights = self.gate_dense(gate_ctx)  # (batch, num_modalities)
        gate_weights = tf.expand_dims(gate_weights, axis=-1)  # (batch, num_modalities, 1)

        # Weighted sum of projected modalities
        fused = tf.reduce_sum(stacked * gate_weights, axis=1)  # (batch, output_dim)

        # Final projection
        fused = self.fusion_dense(fused)
        fused = self.fusion_norm(fused)
        fused = self.fusion_drop(fused, training=training)
        return fused

    def get_config(self):
        config = super().get_config()
        config.update({
            "output_dim": self.output_dim,
            "num_modalities": self.num_modalities,
        })
        return config


class ConcatFusionLayer(layers.Layer):
    """
    Simple concatenation + dense projection fusion.
    Faster but less flexible than gated fusion.
    """

    def __init__(self, output_dim: int = 512, dropout_rate: float = 0.3, **kwargs):
        super().__init__(**kwargs)
        self.concat = layers.Concatenate(name="feature_concat")
        self.dense1 = layers.Dense(1024, activation="relu", name="fusion_d1")
        self.bn1 = layers.BatchNormalization(name="fusion_bn1")
        self.drop1 = layers.Dropout(dropout_rate, name="fusion_drop1")
        self.dense2 = layers.Dense(output_dim, activation="relu", name="fusion_d2")
        self.bn2 = layers.BatchNormalization(name="fusion_bn2")

    def call(self, features: List[tf.Tensor], training: bool = False) -> tf.Tensor:
        x = self.concat(features)
        x = self.dense1(x)
        x = self.bn1(x, training=training)
        x = self.drop1(x, training=training)
        x = self.dense2(x)
        x = self.bn2(x, training=training)
        return x

    def get_config(self):
        config = super().get_config()
        config.update({"output_dim": self.dense2.units})
        return config


def build_fusion_model(
    cnn_dim: int = 512,
    vit_dim: int = 512,
    rnn_dim: int = 256,
    context_dim: int = 64,
    output_dim: int = 512,
    fusion_type: str = "gated",
) -> Model:
    """
    Build the feature fusion model combining all modality outputs.

    Inputs:
        - cnn_features: (batch, cnn_dim) — MobileNetV2 spatial features
        - vit_features: (batch, vit_dim) — ViT global context features
        - rnn_features: (batch, rnn_dim) — LSTM temporal/sequential features
        - context_features: (batch, context_dim) — Weather + Maps context

    Output:
        - fused: (batch, output_dim)

    Args:
        fusion_type: "gated" (recommended) or "concat"
    """
    cnn_in = layers.Input(shape=(cnn_dim,), name="cnn_input")
    vit_in = layers.Input(shape=(vit_dim,), name="vit_input")
    rnn_in = layers.Input(shape=(rnn_dim,), name="rnn_input")
    ctx_in = layers.Input(shape=(context_dim,), name="context_input")

    # Project context to match modality dims
    ctx_proj = layers.Dense(256, activation="relu", name="ctx_proj")(ctx_in)
    ctx_proj = layers.LayerNormalization(name="ctx_ln")(ctx_proj)

    if fusion_type == "gated":
        fusion = GatedFusionLayer(output_dim=output_dim, num_modalities=4, name="gated_fusion")
        fused = fusion([cnn_in, vit_in, rnn_in, ctx_proj])
    else:
        fusion = ConcatFusionLayer(output_dim=output_dim)
        fused = fusion([cnn_in, vit_in, rnn_in, ctx_proj])

    model = Model(
        inputs=[cnn_in, vit_in, rnn_in, ctx_in],
        outputs=fused,
        name="feature_fusion_model",
    )
    return model


if __name__ == "__main__":
    model = build_fusion_model()
    model.summary()
    dummy = {
        "cnn": tf.random.normal((4, 512)),
        "vit": tf.random.normal((4, 512)),
        "rnn": tf.random.normal((4, 256)),
        "ctx": tf.random.normal((4, 64)),
    }
    out = model([dummy["cnn"], dummy["vit"], dummy["rnn"], dummy["ctx"]], training=False)
    print(f"Fusion output: {out.shape}")
