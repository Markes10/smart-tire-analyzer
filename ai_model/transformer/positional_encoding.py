"""
Positional encodings for the Tire Vision Transformer.
Provides spatial context for patch tokens so the model knows
where on the tire each patch comes from.
"""

from __future__ import annotations

import importlib
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

TF: Any = tf
KerasLayers: Any = importlib.import_module("tensorflow.keras.layers")
KerasLayerBase: Any = KerasLayers.Layer

LayerConfig: TypeAlias = dict[str, Any]
FloatArray: TypeAlias = npt.NDArray[np.float64]


def _init_keras_layer(instance: object, **kwargs: Any) -> None:
    """Initialize a dynamically imported Keras layer base."""
    layer_base: Any = KerasLayerBase
    layer_base.__init__(instance, **kwargs)


class LearnablePositionalEncoding(KerasLayerBase):
    """
    Learnable positional embeddings preferred for ViT models.
    Each patch position gets a unique trainable embedding vector.
    """

    num_positions: int
    embedding_dim: int
    pos_embedding: Any

    def __init__(self, num_positions: int, embedding_dim: int, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        self.num_positions = num_positions
        self.embedding_dim = embedding_dim
        self.pos_embedding = KerasLayers.Embedding(
            input_dim=num_positions,
            output_dim=embedding_dim,
            name="pos_emb",
        )

    def call(self, x: tf.Tensor) -> tf.Tensor:
        """
        Args:
            x: (batch, seq_len, embedding_dim)
        Returns:
            Tensor with positional embeddings added to the input.
        """
        seq_len = cast(tf.Tensor, TF.shape(x)[1])
        positions = cast(tf.Tensor, TF.range(seq_len))
        pos_emb = cast(tf.Tensor, self.pos_embedding(positions))
        return x + pos_emb

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "num_positions": self.num_positions,
                "embedding_dim": self.embedding_dim,
            }
        )
        return config


class SinusoidalPositionalEncoding(KerasLayerBase):
    """
    Fixed sinusoidal positional encoding from "Attention Is All You Need".
    Useful when sequence length can vary.
    """

    max_len: int
    embedding_dim: int
    encoding: tf.Tensor

    def __init__(self, max_len: int = 197, embedding_dim: int = 256, **kwargs: Any) -> None:
        _init_keras_layer(self, **kwargs)
        self.max_len = max_len
        self.embedding_dim = embedding_dim
        self.encoding = self._build_encoding(max_len, embedding_dim)

    @staticmethod
    def _build_encoding(max_len: int, d_model: int) -> tf.Tensor:
        """Precompute the sinusoidal encoding matrix."""
        positions: FloatArray = np.arange(max_len, dtype=np.float64)[:, np.newaxis]
        dims: FloatArray = np.arange(d_model, dtype=np.float64)[np.newaxis, :]
        angles: FloatArray = positions / np.power(
            10000.0,
            (2.0 * np.floor(dims / 2.0)) / float(d_model),
        )
        angles[:, 0::2] = np.sin(angles[:, 0::2])
        angles[:, 1::2] = np.cos(angles[:, 1::2])
        return cast(tf.Tensor, TF.cast(angles[np.newaxis, :, :], tf.float32))

    def call(self, x: tf.Tensor) -> tf.Tensor:
        seq_len = cast(tf.Tensor, TF.shape(x)[1])
        return x + self.encoding[:, :seq_len, :]

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "max_len": self.max_len,
                "embedding_dim": self.embedding_dim,
            }
        )
        return config


class TwoDimensionalPositionalEncoding(KerasLayerBase):
    """
    2D positional encoding aware of row and column patch positions.
    Lets the model distinguish center, edge, and shoulder regions.
    """

    grid_size: int
    embedding_dim: int
    row_embedding: Any
    col_embedding: Any

    def __init__(
        self,
        grid_size: int = 14,
        embedding_dim: int = 256,
        **kwargs: Any,
    ) -> None:
        _init_keras_layer(self, **kwargs)
        if embedding_dim % 2 != 0:
            raise ValueError("embedding_dim must be even for 2D positional encoding")

        self.grid_size = grid_size
        self.embedding_dim = embedding_dim
        self.row_embedding = KerasLayers.Embedding(
            grid_size,
            embedding_dim // 2,
            name="row_emb",
        )
        self.col_embedding = KerasLayers.Embedding(
            grid_size,
            embedding_dim // 2,
            name="col_emb",
        )

    def call(self, x: tf.Tensor) -> tf.Tensor:
        """
        Args:
            x: (batch, num_patches + 1, embedding_dim)
               Assumes the first token is the CLS token.
        """
        rows = cast(tf.Tensor, TF.range(self.grid_size))
        cols = cast(tf.Tensor, TF.range(self.grid_size))
        row_grid, col_grid = cast(
            tuple[tf.Tensor, tf.Tensor],
            tuple(TF.meshgrid(rows, cols, indexing="ij")),
        )

        flat_rows = cast(tf.Tensor, TF.reshape(row_grid, [-1]))
        flat_cols = cast(tf.Tensor, TF.reshape(col_grid, [-1]))
        row_enc = cast(tf.Tensor, self.row_embedding(flat_rows))
        col_enc = cast(tf.Tensor, self.col_embedding(flat_cols))
        pos_2d = cast(tf.Tensor, TF.concat([row_enc, col_enc], axis=-1))

        cls_pos = cast(tf.Tensor, TF.zeros([1, self.embedding_dim], dtype=x.dtype))
        pos_encodings = cast(tf.Tensor, TF.concat([cls_pos, pos_2d], axis=0))
        return x + pos_encodings

    def get_config(self) -> LayerConfig:
        config = cast(dict[str, Any], KerasLayerBase.get_config(self))
        config.update(
            {
                "grid_size": self.grid_size,
                "embedding_dim": self.embedding_dim,
            }
        )
        return config
