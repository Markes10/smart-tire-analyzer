"""
LSTM/GRU sequence models for tread depth analysis.
"""

from __future__ import annotations

from typing import Any, TypeAlias

import tensorflow as tf

KerasModel: TypeAlias = Any


def build_lstm_tread_model(
    input_dim: int = 64,
    hidden_units: int = 128,
    num_layers: int = 2,
    use_gru: bool = False,
    dropout_rate: float = 0.2,
    output_dim: int = 256,
    return_sequences: bool = False,
) -> KerasModel:
    """
    Build a bidirectional LSTM or GRU model for sequential tread analysis.

    Input shape:
        `(batch, seq_len, input_dim)`

    Output shape:
        `(batch, output_dim)` unless `return_sequences=True`
    """
    tf_module: Any = tf
    keras_layers: Any = tf_module.keras.layers
    keras_model: Any = tf_module.keras.Model

    inputs: Any = keras_layers.Input(shape=(None, input_dim), name="rnn_input")
    x: Any = inputs

    rnn_cell: Any = keras_layers.GRU if use_gru else keras_layers.LSTM
    layer_prefix = "gru" if use_gru else "lstm"

    for i in range(num_layers):
        return_seq = (i < num_layers - 1) or return_sequences
        x = keras_layers.Bidirectional(
            rnn_cell(
                hidden_units,
                return_sequences=return_seq,
                dropout=dropout_rate,
                recurrent_dropout=dropout_rate * 0.5,
                name=f"{layer_prefix}_{i}",
            ),
            name=f"bidir_{i}",
        )(x)
        x = keras_layers.LayerNormalization(name=f"rnn_ln_{i}")(x)

    if not return_sequences:
        x = keras_layers.Dropout(dropout_rate, name="rnn_drop")(x)
        x = keras_layers.Dense(output_dim, activation="relu", name="rnn_proj")(x)
        x = keras_layers.LayerNormalization(name="rnn_out_ln")(x)

    return keras_model(inputs=inputs, outputs=x, name="lstm_tread_model")


def build_attention_rnn(
    input_dim: int = 64,
    hidden_units: int = 128,
    num_heads: int = 4,
    output_dim: int = 256,
    dropout_rate: float = 0.2,
) -> KerasModel:
    """
    Build an LSTM plus self-attention model for tread sequences.

    The attention block helps the model focus on the most informative
    tread positions before projecting to a fixed-width embedding.
    """
    tf_module: Any = tf
    keras_layers: Any = tf_module.keras.layers
    keras_model: Any = tf_module.keras.Model
    keras_ops: Any = tf_module.keras.ops

    inputs: Any = keras_layers.Input(shape=(None, input_dim), name="attn_rnn_input")

    x: Any = keras_layers.Bidirectional(
        keras_layers.LSTM(
            hidden_units,
            return_sequences=True,
            dropout=dropout_rate,
        ),
        name="bilstm",
    )(inputs)
    x = keras_layers.LayerNormalization(name="bilstm_ln")(x)

    attn_out: Any = keras_layers.MultiHeadAttention(
        num_heads=num_heads,
        key_dim=max(1, hidden_units // num_heads),
        dropout=dropout_rate,
        name="seq_attention",
    )(x, x)
    x = keras_layers.Add(name="attn_residual")([x, attn_out])
    x = keras_layers.LayerNormalization(name="attn_ln")(x)

    attn_scores: Any = keras_layers.Dense(1, name="tread_attn_scores")(x)
    attn_weights: Any = keras_layers.Softmax(axis=1, name="tread_attn_weights")(
        attn_scores
    )
    x = keras_layers.Multiply(name="attn_weighted")([x, attn_weights])
    x = keras_ops.sum(x, axis=1)

    x = keras_layers.Dense(output_dim, activation="relu", name="attn_rnn_proj")(x)
    x = keras_layers.LayerNormalization(name="attn_rnn_ln")(x)
    x = keras_layers.Dropout(dropout_rate, name="attn_rnn_drop")(x)

    return keras_model(inputs=inputs, outputs=x, name="attention_rnn")


if __name__ == "__main__":
    tf_module: Any = tf

    model: Any = build_lstm_tread_model()
    model.summary()

    dummy_seq: Any = tf_module.random.normal((8, 4, 64))
    out: Any = model(dummy_seq, training=False)
    print(f"LSTM output shape: {out.shape}")

    attn_model: Any = build_attention_rnn()
    attn_model.summary()

    out2: Any = attn_model(dummy_seq, training=False)
    print(f"Attention-RNN output shape: {out2.shape}")
