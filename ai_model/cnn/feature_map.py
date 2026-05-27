"""
Feature Map Builder — CNN output vector aggregation.
Combines multi-scale CNN features for richer representations.
"""

import tensorflow as tf
from tensorflow.keras import layers, Model
from typing import List, Tuple


class MultiScaleFeatureBuilder(layers.Layer):
    """
    Aggregates feature maps from multiple CNN scales.
    Applies attention-weighted pooling to focus on tread groove regions.
    """

    def __init__(self, output_dim: int = 512, **kwargs):
        super().__init__(**kwargs)
        self.output_dim = output_dim
        self.attention = layers.Dense(1, activation="sigmoid")
        self.projection = layers.Dense(output_dim, activation="relu")
        self.norm = layers.LayerNormalization()

    def call(self, feature_maps: List[tf.Tensor], training=False) -> tf.Tensor:
        """
        Args:
            feature_maps: List of tensors, each (batch, h, w, c)
        Returns:
            Aggregated feature vector (batch, output_dim)
        """
        pooled = []
        for fm in feature_maps:
            # Spatial attention
            attn = self.attention(fm)
            weighted = fm * attn
            pooled.append(tf.reduce_mean(weighted, axis=[1, 2]))

        # Concatenate and project
        x = tf.concat(pooled, axis=-1)
        x = self.projection(x)
        x = self.norm(x)
        return x

    def get_config(self):
        config = super().get_config()
        config.update({"output_dim": self.output_dim})
        return config


def build_feature_pyramid(base_model: Model) -> Model:
    """
    Build a Feature Pyramid Network (FPN) style extractor
    from MobileNetV2 intermediate layers.

    Returns:
        Model with multi-scale outputs (C3, C4, C5)
    """
    # Extract layers at different scales from MobileNetV2
    layer_names = [
        "block_6_expand_relu",     # 28×28 — mid-level
        "block_13_expand_relu",    # 14×14 — high-level
        "out_relu",                # 7×7  — semantic
    ]

    outputs = []
    for name in layer_names:
        try:
            out = base_model.get_layer(name).output
            # Pool to fixed size
            out = layers.GlobalAveragePooling2D()(out)
            outputs.append(out)
        except ValueError:
            pass  # Layer not present in lite version

    return outputs


def build_feature_vector_model(
    cnn_extractor: Model,
    output_dim: int = 512,
) -> Model:
    """
    Wrap CNN extractor with feature pyramid + multi-scale pooling.

    Args:
        cnn_extractor: MobileNetV2 extractor model
        output_dim: Final feature vector dimension

    Returns:
        Model outputting (batch, output_dim) feature vectors
    """
    inputs = cnn_extractor.input
    features = cnn_extractor.output

    # Final dense projection
    x = layers.Dense(output_dim, activation="relu", name="fv_proj")(features)
    x = layers.LayerNormalization(name="fv_ln")(x)
    x = layers.Dropout(0.2, name="fv_drop")(x)

    return Model(inputs=inputs, outputs=x, name="feature_vector_model")
