"""
Multi-head self-attention layers for the Tire Vision Transformer.
Includes attention-weight access for explainability tooling.
"""

from __future__ import annotations

import importlib
from typing import Any, TypeAlias, cast

import tensorflow as tf

TF: Any = tf
KerasLayers: Any = importlib.import_module("tensorflow.keras.layers")
KerasLayerBase: Any = KerasLayers.Layer

AttentionInputs: TypeAlias = tuple[tf.Tensor, tf.Tensor, tf.Tensor]
CrossAttentionInputs: TypeAlias = tuple[tf.Tensor, tf.Tensor]
LayerConfig: TypeAlias = dict[str, int | float | str]


def _init_keras_layer(instance: object, **kwargs: Any) -> None:
    """Initialize a dynamically imported Keras layer base."""
    layer_base: Any = KerasLayerBase
    layer_base.__init__(instance, **kwargs)


def _resolve_attention_mask(mask: object | None) -> tf.Tensor | None:
    """Normalize Keras-provided mask values for tuple inputs."""
    if mask is None:
        return None
    if isinstance(mask, tuple):
        for item in cast(tuple[object, ...], mask):
            if item is not None:
                return cast(tf.Tensor, item)
        return None
    if isinstance(mask, list):
        for item in cast(list[object], mask):
            if item is not None:
                return cast(tf.Tensor, item)
        return None
    return cast(tf.Tensor, mask)


class TireAttentionHead(KerasLayerBase):
    """
    Single scaled dot-product attention head.
    Captures relationships between tire tread patches.
    """

    key_dim: int
    scale: tf.Tensor
    q_proj: Any
    k_proj: Any
    v_proj: Any
    dropout: Any
    attention_weights: tf.Tensor | None

    def __init__(self, key_dim: int, dropout_rate: float = 0.1, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        self.key_dim = key_dim
        self.scale = cast(tf.Tensor, TF.math.sqrt(TF.cast(key_dim, tf.float32)))
        self.q_proj = KerasLayers.Dense(key_dim, use_bias=False)
        self.k_proj = KerasLayers.Dense(key_dim, use_bias=False)
        self.v_proj = KerasLayers.Dense(key_dim, use_bias=False)
        self.dropout = KerasLayers.Dropout(dropout_rate)
        self.attention_weights = None

    def call(
        self,
        inputs: AttentionInputs,
        training: bool | None = None,
        mask: object | None = None,
    ) -> tuple[tf.Tensor, tf.Tensor]:
        """
        Args:
            inputs: (query, key, value), each shaped (batch, seq_len, d_model)
            mask: optional attention mask
        Returns:
            output: (batch, seq_len, key_dim)
            attention_weights: (batch, seq_len, seq_len)
        """
        training_flag = bool(training) if training is not None else False
        query, key, value = inputs
        attention_mask = _resolve_attention_mask(mask)

        q = cast(tf.Tensor, self.q_proj(query))
        k = cast(tf.Tensor, self.k_proj(key))
        v = cast(tf.Tensor, self.v_proj(value))

        scores = cast(tf.Tensor, TF.matmul(q, k, transpose_b=True) / self.scale)
        if attention_mask is not None:
            scores = scores + attention_mask * -1e9

        raw_attention = cast(tf.Tensor, TF.nn.softmax(scores, axis=-1))
        self.attention_weights = raw_attention

        dropped_attention = cast(
            tf.Tensor,
            self.dropout(raw_attention, training=training_flag),
        )
        output = cast(tf.Tensor, TF.matmul(dropped_attention, v))
        return output, dropped_attention

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update({"key_dim": self.key_dim})
        return cast(LayerConfig, config)


class MultiHeadTireAttention(KerasLayerBase):
    """
    Multi-head self-attention for tire image patches.
    Enables the model to jointly attend to information from different
    representation subspaces such as grooves, edges, and wear zones.
    """

    embedding_dim: int
    num_heads: int
    key_dim: int
    heads: list[TireAttentionHead]
    output_proj: Any
    dropout: Any

    def __init__(
        self,
        embedding_dim: int,
        num_heads: int = 8,
        dropout_rate: float = 0.1,
        **kwargs: Any,
    ) -> None:
        _init_keras_layer(self, **kwargs)
        if embedding_dim % num_heads != 0:
            raise ValueError(
                f"embedding_dim ({embedding_dim}) must be divisible by num_heads ({num_heads})"
            )

        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.key_dim = embedding_dim // num_heads
        self.heads = [
            TireAttentionHead(self.key_dim, dropout_rate)
            for _ in range(num_heads)
        ]
        self.output_proj = KerasLayers.Dense(embedding_dim)
        self.dropout = KerasLayers.Dropout(dropout_rate)

    def call(
        self,
        inputs: tf.Tensor,
        training: bool | None = None,
        mask: tf.Tensor | None = None,
    ) -> tf.Tensor:
        """
        Args:
            inputs: (batch, seq_len, embedding_dim)
        Returns:
            output: (batch, seq_len, embedding_dim)
        """
        training_flag = bool(training) if training is not None else False
        head_outputs: list[tf.Tensor] = []
        for head in self.heads:
            output, _ = head((inputs, inputs, inputs), training=training_flag, mask=mask)
            head_outputs.append(output)

        concatenated = cast(tf.Tensor, TF.concat(head_outputs, axis=-1))
        projected = cast(tf.Tensor, self.output_proj(concatenated))
        return cast(tf.Tensor, self.dropout(projected, training=training_flag))

    def get_attention_maps(self) -> list[tf.Tensor]:
        """Return stored attention maps from all heads for visualization."""
        attention_maps: list[tf.Tensor] = []
        for head in self.heads:
            weights = head.attention_weights
            if weights is not None:
                attention_maps.append(weights)
        return attention_maps

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "embedding_dim": self.embedding_dim,
                "num_heads": self.num_heads,
            }
        )
        return cast(LayerConfig, config)


class CrossAttentionFusion(KerasLayerBase):
    """
    Cross-attention between CNN features and ViT patch tokens.
    CNN features act as queries; ViT patches act as keys and values.
    """

    dim: int
    num_heads: int
    attn: Any
    norm_q: Any
    norm_kv: Any
    proj: Any

    def __init__(self, dim: int, num_heads: int = 4, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        self.dim = dim
        self.num_heads = num_heads
        self.attn = KerasLayers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=dim // num_heads,
            name="cross_attn",
        )
        self.norm_q = KerasLayers.LayerNormalization()
        self.norm_kv = KerasLayers.LayerNormalization()
        self.proj = KerasLayers.Dense(dim)

    def call(
        self,
        inputs: CrossAttentionInputs,
        training: bool | None = None,
        mask: object | None = None,
    ) -> tf.Tensor:
        """
        Args:
            inputs: (cnn_features, vit_patches)
                cnn_features: (batch, cnn_dim)
                vit_patches: (batch, num_patches, vit_dim)
        Returns:
            fused: (batch, dim)
        """
        del mask
        training_flag = bool(training) if training is not None else False
        cnn_features, vit_patches = inputs

        query = cast(tf.Tensor, TF.expand_dims(cnn_features, axis=1))
        query = cast(tf.Tensor, self.norm_q(query))
        key_value = cast(tf.Tensor, self.norm_kv(vit_patches))

        attn_out = cast(
            tf.Tensor,
            self.attn(query=query, key=key_value, value=key_value, training=training_flag),
        )
        squeezed = cast(tf.Tensor, TF.squeeze(attn_out, axis=1))
        return cast(tf.Tensor, self.proj(squeezed))

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "dim": self.dim,
                "num_heads": self.num_heads,
            }
        )
        return cast(LayerConfig, config)
