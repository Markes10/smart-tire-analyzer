"""
Vision Transformer (ViT) encoder for tire feature extraction.
Implements patch embedding and transformer blocks for global
spatial relationships in tire tread patterns.
"""

from __future__ import annotations

import importlib
from typing import Any, TypeAlias, cast

import tensorflow as tf

from ai_model.transformer.positional_encoding import LearnablePositionalEncoding

TF: Any = tf
KerasAPI: Any = importlib.import_module("tensorflow.keras")
KerasLayers: Any = KerasAPI.layers
KerasLayerBase: Any = KerasLayers.Layer
KerasModelBase: Any = KerasAPI.Model
KerasSequential: Any = KerasAPI.Sequential

InputShape: TypeAlias = tuple[int, int, int]
LayerConfig: TypeAlias = dict[str, Any]
ModelLike: TypeAlias = Any


def _init_keras_layer(instance: object, **kwargs: Any) -> None:
    """Initialize a dynamically imported Keras layer base."""
    layer_base: Any = KerasLayerBase
    layer_base.__init__(instance, **kwargs)


def _require_dimension(value: int, name: str) -> int:
    """Validate static image shape values used to size ViT patches."""
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, received {value}")
    return value


class PatchEmbedding(KerasLayerBase):
    """
    Split an image into non-overlapping patches and project each patch.
    """

    patch_size: int
    embedding_dim: int
    projection: Any

    def __init__(self, patch_size: int = 16, embedding_dim: int = 256, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        if patch_size <= 0:
            raise ValueError(f"patch_size must be positive, received {patch_size}")

        self.patch_size = patch_size
        self.embedding_dim = embedding_dim
        self.projection = KerasLayers.Dense(embedding_dim, name="patch_proj")

    def call(self, images: tf.Tensor) -> tf.Tensor:
        """
        Args:
            images: (batch, height, width, channels)
        Returns:
            Patch embeddings with shape (batch, num_patches, embedding_dim).
        """
        batch_size = cast(tf.Tensor, TF.shape(images)[0])
        patches = cast(
            tf.Tensor,
            TF.image.extract_patches(
                images,
                sizes=[1, self.patch_size, self.patch_size, 1],
                strides=[1, self.patch_size, self.patch_size, 1],
                rates=[1, 1, 1, 1],
                padding="VALID",
            ),
        )
        patch_dim = cast(tf.Tensor, TF.shape(patches)[-1])
        flat_patches = cast(tf.Tensor, TF.reshape(patches, [batch_size, -1, patch_dim]))
        return cast(tf.Tensor, self.projection(flat_patches))

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "patch_size": self.patch_size,
                "embedding_dim": self.embedding_dim,
            }
        )
        return config


class ClassToken(KerasLayerBase):
    """
    Prepend a learned CLS token to the patch sequence.
    """

    embedding_dim: int
    cls_token: tf.Tensor

    def __init__(self, embedding_dim: int = 256, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        self.embedding_dim = embedding_dim
        self.cls_token = cast(tf.Tensor, TF.zeros((1, 1, embedding_dim), dtype=tf.float32))

    def build(self, input_shape: object) -> None:
        layer_self: Any = self
        self.cls_token = cast(
            tf.Tensor,
            layer_self.add_weight(
                name="cls_token",
                shape=(1, 1, self.embedding_dim),
                initializer="zeros",
                trainable=True,
            ),
        )
        layer_base: Any = KerasLayerBase
        layer_base.build(self, input_shape)

    def call(self, patches: tf.Tensor) -> tf.Tensor:
        batch_size = cast(tf.Tensor, TF.shape(patches)[0])
        cls_tokens = cast(
            tf.Tensor,
            TF.broadcast_to(self.cls_token, [batch_size, 1, self.embedding_dim]),
        )
        return cast(tf.Tensor, TF.concat([cls_tokens, patches], axis=1))

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update({"embedding_dim": self.embedding_dim})
        return config


class TransformerBlock(KerasLayerBase):
    """
    Single transformer encoder block with pre-normalization and residuals.
    """

    embedding_dim: int
    num_heads: int
    mlp_ratio: float
    dropout_rate: float
    attention_dropout: float
    norm1: Any
    attn: Any
    attn_drop: Any
    norm2: Any
    ffn: Any

    def __init__(
        self,
        embedding_dim: int,
        num_heads: int = 8,
        mlp_ratio: float = 4.0,
        dropout_rate: float = 0.1,
        attention_dropout: float = 0.1,
        **kwargs: Any,
    ) -> None:
        _init_keras_layer(self, **kwargs)
        if embedding_dim % num_heads != 0:
            raise ValueError(
                f"embedding_dim ({embedding_dim}) must be divisible by num_heads ({num_heads})"
            )

        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.mlp_ratio = mlp_ratio
        self.dropout_rate = dropout_rate
        self.attention_dropout = attention_dropout

        self.norm1 = KerasLayers.LayerNormalization(epsilon=1e-6)
        self.attn = KerasLayers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=embedding_dim // num_heads,
            dropout=attention_dropout,
        )
        self.attn_drop = KerasLayers.Dropout(dropout_rate)

        mlp_dim = int(embedding_dim * mlp_ratio)
        self.norm2 = KerasLayers.LayerNormalization(epsilon=1e-6)
        self.ffn = KerasSequential(
            [
                KerasLayers.Dense(mlp_dim, activation="gelu"),
                KerasLayers.Dropout(dropout_rate),
                KerasLayers.Dense(embedding_dim),
                KerasLayers.Dropout(dropout_rate),
            ]
        )

    def call(self, x: tf.Tensor, training: bool | None = None) -> tf.Tensor:
        training_flag = bool(training) if training is not None else False

        x_norm = cast(tf.Tensor, self.norm1(x))
        attn_out = cast(
            tf.Tensor,
            self.attn(query=x_norm, value=x_norm, training=training_flag),
        )
        attn_out = cast(tf.Tensor, self.attn_drop(attn_out, training=training_flag))
        residual = x + attn_out

        ffn_input = cast(tf.Tensor, self.norm2(residual))
        ffn_out = cast(tf.Tensor, self.ffn(ffn_input, training=training_flag))
        return residual + ffn_out

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "embedding_dim": self.embedding_dim,
                "num_heads": self.num_heads,
                "mlp_ratio": self.mlp_ratio,
                "dropout_rate": self.dropout_rate,
                "attention_dropout": self.attention_dropout,
            }
        )
        return config


def build_vit_encoder(
    input_shape: InputShape = (224, 224, 4),
    patch_size: int = 16,
    embedding_dim: int = 256,
    num_heads: int = 8,
    num_transformer_blocks: int = 6,
    mlp_ratio: float = 4.0,
    dropout_rate: float = 0.1,
    output_dim: int = 512,
) -> ModelLike:
    """
    Build the full Vision Transformer encoder.

    Returns:
        Keras model outputting (batch, output_dim) features.
    """
    image_height = _require_dimension(input_shape[0], "input_shape[0]")
    image_width = _require_dimension(input_shape[1], "input_shape[1]")

    if image_height % patch_size != 0 or image_width % patch_size != 0:
        raise ValueError(
            "input_shape height and width must be divisible by patch_size; "
            f"received input_shape={input_shape}, patch_size={patch_size}"
        )

    num_patches = (image_height // patch_size) * (image_width // patch_size)

    inputs = cast(tf.Tensor, KerasLayers.Input(shape=input_shape, name="vit_input"))

    x = cast(
        tf.Tensor,
        PatchEmbedding(
            patch_size=patch_size,
            embedding_dim=embedding_dim,
            name="patch_embedding",
        )(inputs),
    )
    x = cast(
        tf.Tensor,
        ClassToken(embedding_dim=embedding_dim, name="cls_token")(x),
    )
    x = cast(
        tf.Tensor,
        LearnablePositionalEncoding(
            num_positions=num_patches + 1,
            embedding_dim=embedding_dim,
            name="pos_encoding",
        )(x),
    )
    x = cast(tf.Tensor, KerasLayers.Dropout(dropout_rate)(x))

    for index in range(num_transformer_blocks):
        x = cast(
            tf.Tensor,
            TransformerBlock(
                embedding_dim=embedding_dim,
                num_heads=num_heads,
                mlp_ratio=mlp_ratio,
                dropout_rate=dropout_rate,
                attention_dropout=dropout_rate,
                name=f"transformer_block_{index}",
            )(x),
        )

    x = cast(tf.Tensor, KerasLayers.LayerNormalization(epsilon=1e-6, name="vit_final_ln")(x))
    cls_output = x[:, 0, :]
    x = cast(tf.Tensor, KerasLayers.Dense(output_dim, activation="relu", name="vit_proj")(cls_output))
    x = cast(tf.Tensor, KerasLayers.LayerNormalization(name="vit_out_ln")(x))
    outputs = cast(tf.Tensor, KerasLayers.Dropout(dropout_rate, name="vit_out_drop")(x))

    model = KerasModelBase(inputs=inputs, outputs=outputs, name="vit_encoder")
    return model


if __name__ == "__main__":
    model = build_vit_encoder()
    model.summary()
    dummy = cast(tf.Tensor, TF.random.normal((2, 224, 224, 4)))
    out = cast(tf.Tensor, model(dummy, training=False))
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("ViT output shape: %s", out.shape)
