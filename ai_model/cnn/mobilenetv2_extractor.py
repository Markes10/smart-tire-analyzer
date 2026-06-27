"""
MobileNetV2 Feature Extraction Backbone
CNN component of the Smart Tire Analyzer AI pipeline.
Extracts rich spatial features from preprocessed tire images.
"""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false

from __future__ import annotations

from typing import Any, TypeAlias, cast

import keras
from keras import KerasTensor


ModelLike: TypeAlias = Any


def _apply(layer: Any, inputs: KerasTensor, /, **kwargs: Any) -> KerasTensor:
    """Cast symbolic layer outputs so static analysis stays usable with Keras."""
    return cast(KerasTensor, layer(inputs, **kwargs))


def build_mobilenetv2_extractor(
    input_shape: tuple[int, int, int] = (224, 224, 4),
    trainable_layers: int = 30,
    dropout_rate: float = 0.3,
) -> ModelLike:
    """
    Build MobileNetV2-based CNN feature extractor.
    Supports 4-channel input (RGB + edge map) as per preprocessing pipeline.

    Args:
        input_shape: (H, W, C) - default 224x224 with 4 channels (RGB + edges)
        trainable_layers: Number of top layers to unfreeze for fine-tuning
        dropout_rate: Spatial dropout rate after feature extraction

    Returns:
        Keras Model that outputs a (batch, 512) feature vector
    """
    inputs: KerasTensor = cast(KerasTensor, keras.Input(shape=input_shape, name="cnn_input"))
    x: KerasTensor = inputs

    # If 4-channel input, project to 3 channels for MobileNetV2 compatibility.
    if input_shape[-1] == 4:
        x = _apply(
            keras.layers.Conv2D(
                3,
                (1, 1),
                padding="same",
                use_bias=False,
                name="channel_proj",
            ),
            x,
        )
        x = _apply(keras.layers.BatchNormalization(name="channel_proj_bn"), x)
        x = _apply(keras.layers.ReLU(name="channel_proj_relu"), x)

    # Load MobileNetV2 pretrained on ImageNet, exclude top classifier.
    base_model: Any = cast(
        Any,
        keras.applications.MobileNetV2(
            input_shape=(224, 224, 3),
            include_top=False,
            weights="imagenet",
            pooling=None,
        ),
    )

    # Freeze all layers first.
    base_model.trainable = False

    # Unfreeze the top N layers for domain adaptation.
    if trainable_layers > 0:
        for layer in cast(list[Any], base_model.layers[-trainable_layers:]):
            if not isinstance(layer, keras.layers.BatchNormalization):
                layer.trainable = True

    # Feature extraction.
    x = _apply(base_model, x, training=False)

    # Global Average Pooling -> (batch, 1280).
    x = _apply(keras.layers.GlobalAveragePooling2D(name="cnn_gap"), x)

    # Dropout for regularization.
    x = _apply(keras.layers.Dropout(dropout_rate, name="cnn_dropout"), x)

    # Final feature projection.
    x = _apply(keras.layers.Dense(512, activation="relu", name="cnn_proj"), x)
    x = _apply(keras.layers.LayerNormalization(name="cnn_ln"), x)

    model: ModelLike = keras.Model(
        inputs=inputs,
        outputs=x,
        name="mobilenetv2_extractor",
    )
    return model


def build_lite_cnn_extractor(
    input_shape: tuple[int, int, int] = (224, 224, 4),
) -> ModelLike:
    """
    Lightweight CNN extractor for low-resource / mobile inference.
    Used when MobileNetV2 weights are not available (offline mode).
    """
    inputs: KerasTensor = cast(KerasTensor, keras.Input(shape=input_shape, name="lite_cnn_input"))

    x = _apply(keras.layers.Conv2D(32, (3, 3), padding="same", activation="relu"), inputs)
    x = _apply(keras.layers.BatchNormalization(), x)
    x = _apply(keras.layers.MaxPooling2D((2, 2)), x)

    x = _apply(keras.layers.Conv2D(64, (3, 3), padding="same", activation="relu"), x)
    x = _apply(keras.layers.BatchNormalization(), x)
    x = _apply(keras.layers.MaxPooling2D((2, 2)), x)

    x = _apply(keras.layers.Conv2D(128, (3, 3), padding="same", activation="relu"), x)
    x = _apply(keras.layers.BatchNormalization(), x)
    x = _apply(keras.layers.SpatialDropout2D(0.3), x)
    x = _apply(keras.layers.MaxPooling2D((2, 2)), x)

    x = _apply(keras.layers.Conv2D(256, (3, 3), padding="same", activation="relu"), x)
    x = _apply(keras.layers.BatchNormalization(), x)
    x = _apply(keras.layers.GlobalAveragePooling2D(), x)

    x = _apply(keras.layers.Dense(512, activation="relu"), x)
    x = _apply(keras.layers.LayerNormalization(), x)

    return keras.Model(inputs=inputs, outputs=x, name="lite_cnn_extractor")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    model = build_mobilenetv2_extractor()
    model.summary()
    logger.debug("Output shape: %s", model.output_shape)
    logger.debug("Trainable params: %s", f"{model.count_params():,}")
