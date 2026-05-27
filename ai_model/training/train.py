"""
Smart Tire Analyzer complete hybrid model and training loop.
Assembles CNN, ViT, RNN, and context features into a unified trainable model.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_model.training.callbacks import build_callbacks
from ai_model.training.loss_functions import SmartTireLoss
from ai_model.training.optimizer import OptimizerType, build_optimizer, build_warmup_schedule

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

IMAGE_SHAPE = (224, 224, 4)
TREAD_SEQ_LEN = 4
TREAD_FEAT_DIM = 64
CONTEXT_DIM = 64
DEFAULT_CONTEXT_WIDTH = CONTEXT_DIM

Float32Array: TypeAlias = npt.NDArray[np.float32]
StringSequence: TypeAlias = Sequence[str] | npt.NDArray[np.str_]
TensorMap: TypeAlias = dict[str, tf.Tensor]
LabelArrayMap: TypeAlias = dict[str, Float32Array | npt.NDArray[np.int32]]
HistoryDict: TypeAlias = dict[str, list[float]]
DatasetType: TypeAlias = Any
MetricType: TypeAlias = Any
CallbackType: TypeAlias = Any
AugmentFn: TypeAlias = Callable[[Float32Array], Float32Array]

TF: Any = tf
KerasAPI: Any = importlib.import_module("tensorflow.keras")
KerasModelBase: Any = KerasAPI.Model
KerasLayers: Any = KerasAPI.layers
KerasSequential: Any = KerasAPI.Sequential
KerasMetrics: Any = KerasAPI.metrics
MixedPrecisionAPI: Any = KerasAPI.mixed_precision

CNNExtractorModule: Any = importlib.import_module("ai_model.cnn.mobilenetv2_extractor")
ViTModule: Any = importlib.import_module("ai_model.transformer.vit_encoder")
RNNModule: Any = importlib.import_module("ai_model.rnn.lstm_tread")
FusionModule: Any = importlib.import_module("ai_model.ann.fusion_layer")
PredictionModule: Any = importlib.import_module("ai_model.ann.prediction_head")

build_mobilenetv2_extractor: Any = CNNExtractorModule.build_mobilenetv2_extractor
build_vit_encoder: Any = ViTModule.build_vit_encoder
build_lstm_tread_model: Any = RNNModule.build_lstm_tread_model
build_fusion_model: Any = FusionModule.build_fusion_model
build_prediction_head: Any = PredictionModule.build_prediction_head


def _to_float(value: object) -> float:
    """Convert TensorFlow and NumPy scalar-like values into Python floats."""
    candidate: object = value
    if hasattr(candidate, "numpy"):
        candidate = cast(Any, candidate).numpy()
    if isinstance(candidate, np.ndarray):
        candidate = cast(object, candidate.item())
    if isinstance(candidate, np.generic):
        candidate = cast(object, candidate.item())
    if isinstance(candidate, (bool, int, float)):
        return float(candidate)
    raise TypeError(f"Expected float-like value, received {type(candidate).__name__}")


def _dataset_length(dataset: DatasetType) -> int:
    """Resolve dataset length, falling back to TensorFlow cardinality when needed."""
    dataset_any: Any = dataset
    try:
        return int(len(dataset_any))
    except TypeError:
        cardinality = TF.data.experimental.cardinality(dataset_any)
        return int(_to_float(cardinality))


def _current_learning_rate(optimizer: OptimizerType) -> float:
    """Extract the current learning rate from an optimizer or schedule."""
    optimizer_any: Any = optimizer
    learning_rate: Any = optimizer_any.learning_rate
    value: object = learning_rate(optimizer_any.iterations) if callable(learning_rate) else learning_rate
    return _to_float(value)


def _init_keras_model(instance: object, **kwargs: Any) -> None:
    """Initialize the dynamic Keras model base through a narrow Any boundary."""
    keras_model_base: Any = KerasModelBase
    keras_model_base.__init__(instance, **kwargs)


class SmartTireModel(KerasModelBase):
    """
    Complete Smart Tire Analyzer model.

    Forward pass:
        image -> CNN -> (512,)
        image -> ViT -> (512,)
        tread_sequence -> RNN -> (256,)
        context -> fusion context projection -> (512,)
        -> Fusion -> (512,)
        -> Prediction head -> output dict
    """

    cnn: Any
    vit: Any
    rnn: Any
    context_adapter: Any
    fusion: Any
    prediction_head: Any

    def __init__(
        self,
        cnn_trainable_layers: int = 30,
        vit_blocks: int = 6,
        rnn_hidden: int = 128,
        fused_dim: int = 512,
        dropout_rate: float = 0.25,
        fusion_type: str = "gated",
        tread_feat_dim: int = TREAD_FEAT_DIM,
        context_input_dim: int = CONTEXT_DIM,
        **kwargs: Any,
    ) -> None:
        _init_keras_model(self, **kwargs)
        self.tread_feat_dim = int(tread_feat_dim)
        self.context_input_dim = int(context_input_dim)
        self.cnn = build_mobilenetv2_extractor(
            input_shape=IMAGE_SHAPE,
            trainable_layers=cnn_trainable_layers,
        )
        self.vit = build_vit_encoder(
            input_shape=IMAGE_SHAPE,
            num_transformer_blocks=vit_blocks,
        )
        self.rnn = build_lstm_tread_model(
            input_dim=self.tread_feat_dim,
            hidden_units=rnn_hidden,
            output_dim=256,
        )
        self.context_adapter = (
            None
            if self.context_input_dim == CONTEXT_DIM
            else KerasSequential(
                [
                    KerasLayers.Dense(CONTEXT_DIM, activation="relu"),
                    KerasLayers.LayerNormalization(),
                ],
                name="context_adapter",
            )
        )
        self.fusion = build_fusion_model(
            cnn_dim=512,
            vit_dim=512,
            rnn_dim=256,
            context_dim=CONTEXT_DIM,
            output_dim=fused_dim,
            fusion_type=fusion_type,
        )
        self.prediction_head = build_prediction_head(
            fused_dim=fused_dim,
            dropout_rate=dropout_rate,
        )

    def call(
        self,
        inputs: Mapping[str, tf.Tensor],
        training: bool | None = None,
        mask: object | None = None,
    ) -> TensorMap:
        del mask
        training_flag = bool(training) if training is not None else False

        image = inputs["image"]
        tread_seq = inputs["tread_sequence"]
        context_raw = inputs.get("context")
        if context_raw is None:
            batch_size = cast(tf.Tensor, TF.shape(image)[0])
            context_raw = cast(
                tf.Tensor,
                TF.zeros([batch_size, DEFAULT_CONTEXT_WIDTH], dtype=tf.float32),
            )

        cnn_feat = cast(tf.Tensor, self.cnn(image, training=training_flag))
        vit_feat = cast(tf.Tensor, self.vit(image, training=training_flag))
        rnn_feat = cast(tf.Tensor, self.rnn(tread_seq, training=training_flag))
        ctx_feat = (
            cast(tf.Tensor, context_raw)
            if self.context_adapter is None
            else cast(tf.Tensor, self.context_adapter(context_raw, training=training_flag))
        )
        fused = cast(
            tf.Tensor,
            self.fusion([cnn_feat, vit_feat, rnn_feat, ctx_feat], training=training_flag),
        )
        return cast(TensorMap, self.prediction_head(fused, training=training_flag))

    def build_graph(self) -> TensorMap:
        """Force model build by running a dummy forward pass."""
        dummy_inputs: TensorMap = {
            "image": cast(tf.Tensor, TF.zeros([1, *IMAGE_SHAPE], dtype=tf.float32)),
            "tread_sequence": cast(
                tf.Tensor,
                TF.zeros([1, TREAD_SEQ_LEN, self.tread_feat_dim], dtype=tf.float32),
            ),
            "context": cast(
                tf.Tensor,
                TF.zeros([1, self.context_input_dim], dtype=tf.float32),
            ),
        }
        return self(dummy_inputs, training=False)


def build_tf_dataset(
    image_paths: StringSequence,
    labels: LabelArrayMap,
    tread_sequences: Float32Array,
    contexts: Float32Array | None = None,
    batch_size: int = 16,
    training: bool = True,
    augment_fn: AugmentFn | None = None,
) -> DatasetType:
    """Build a tf.data dataset for training or validation."""
    del augment_fn

    def load_and_preprocess(
        img_path: tf.Tensor,
        label: Any,
        seq: tf.Tensor,
        ctx: tf.Tensor,
    ) -> tuple[TensorMap, Any]:
        img = cast(tf.Tensor, TF.io.read_file(img_path))
        img = cast(tf.Tensor, TF.image.decode_jpeg(img, channels=3))
        img = cast(tf.Tensor, TF.image.resize(img, [224, 224]))
        img = cast(tf.Tensor, TF.cast(img, tf.float32) / 255.0)
        edge = cast(tf.Tensor, TF.reduce_mean(img, axis=-1, keepdims=True))
        image_with_edge = cast(tf.Tensor, TF.concat([img, edge], axis=-1))
        input_batch: TensorMap = {
            "image": image_with_edge,
            "tread_sequence": seq,
            "context": ctx,
        }
        return input_batch, label

    sample_count = len(image_paths)
    context_data = (
        contexts
        if contexts is not None
        else np.zeros((sample_count, DEFAULT_CONTEXT_WIDTH), dtype=np.float32)
    )

    dataset: DatasetType = TF.data.Dataset.from_tensor_slices(
        (
            image_paths,
            labels,
            tread_sequences,
            context_data,
        )
    )

    if training:
        dataset = dataset.shuffle(
            buffer_size=min(sample_count, 1000),
            reshuffle_each_iteration=True,
        )

    dataset = dataset.map(load_and_preprocess, num_parallel_calls=TF.data.AUTOTUNE)
    dataset = dataset.batch(batch_size, drop_remainder=training)
    dataset = dataset.prefetch(TF.data.AUTOTUNE)
    return dataset


def train(
    model: SmartTireModel,
    train_ds: DatasetType,
    val_ds: DatasetType,
    epochs: int = 50,
    learning_rate: float = 1e-4,
    warmup_epochs: int = 5,
    output_dir: str = "ai_model/saved_models",
    use_mixed_precision: bool = True,
) -> HistoryDict:
    """
    Main training loop with mixed precision, multi-task loss, and checkpointing.
    """
    os.makedirs(output_dir, exist_ok=True)

    if use_mixed_precision:
        policy: Any = MixedPrecisionAPI.Policy("mixed_float16")
        MixedPrecisionAPI.set_global_policy(policy)
        logger.info("Mixed precision (float16) enabled")

    steps_per_epoch = _dataset_length(train_ds)
    total_steps = steps_per_epoch * epochs
    warmup_steps = steps_per_epoch * warmup_epochs

    lr_schedule = build_warmup_schedule(
        peak_lr=learning_rate,
        warmup_steps=warmup_steps,
        total_steps=total_steps,
    )
    optimizer: OptimizerType = build_optimizer(
        lr_schedule,
        use_mixed_precision=use_mixed_precision,
    )
    loss_fn = SmartTireLoss()

    train_loss: MetricType = KerasMetrics.Mean(name="train_loss")
    val_loss: MetricType = KerasMetrics.Mean(name="val_loss")
    callbacks: list[CallbackType] = list(build_callbacks(output_dir))

    best_val_loss = float("inf")
    history: HistoryDict = {"train_loss": [], "val_loss": [], "lr": []}

    def _train_step(batch_inputs: TensorMap, batch_labels: TensorMap) -> tf.Tensor:
        with TF.GradientTape() as tape:
            predictions = model(batch_inputs, training=True)
            loss = loss_fn(batch_labels, predictions)
            scaled_loss: tf.Tensor | None = None
            if use_mixed_precision:
                scaled_loss = cast(tf.Tensor, optimizer.get_scaled_loss(loss))

        if use_mixed_precision and scaled_loss is not None:
            scaled_grads: Any = tape.gradient(scaled_loss, model.trainable_variables)
            grads: Any = optimizer.get_unscaled_gradients(scaled_grads)
        else:
            grads = tape.gradient(loss, model.trainable_variables)

        clipped_grads, _ = TF.clip_by_global_norm(grads, clip_norm=1.0)
        optimizer.apply_gradients(zip(clipped_grads, model.trainable_variables))
        return loss

    def _val_step(batch_inputs: TensorMap, batch_labels: TensorMap) -> tf.Tensor:
        predictions = model(batch_inputs, training=False)
        loss = loss_fn(batch_labels, predictions)
        return loss

    train_step = cast(Callable[[TensorMap, TensorMap], tf.Tensor], TF.function(_train_step))
    val_step = cast(Callable[[TensorMap, TensorMap], tf.Tensor], TF.function(_val_step))

    logger.info("Starting training - %d epochs, %d steps/epoch", epochs, steps_per_epoch)
    logger.info("Model parameters: %s", f"{model.count_params():,}")

    for epoch in range(1, epochs + 1):
        start = time.time()
        train_loss.reset_state()
        val_loss.reset_state()

        for step, batch in enumerate(train_ds):
            inputs, labels = cast(tuple[TensorMap, TensorMap], batch)
            loss = train_step(inputs, labels)
            train_loss.update_state(loss)

            if step % 10 == 0:
                current_lr = _current_learning_rate(optimizer)
                logger.debug(
                    "Epoch %d Step %d - loss: %.4f lr: %.6f",
                    epoch,
                    step,
                    _to_float(loss),
                    current_lr,
                )

        for batch in val_ds:
            inputs, labels = cast(tuple[TensorMap, TensorMap], batch)
            loss = val_step(inputs, labels)
            val_loss.update_state(loss)

        train_value = _to_float(train_loss.result())
        val_value = _to_float(val_loss.result())
        current_lr = _current_learning_rate(optimizer)
        elapsed = time.time() - start

        history["train_loss"].append(train_value)
        history["val_loss"].append(val_value)
        history["lr"].append(current_lr)

        logger.info(
            "Epoch %3d/%d - train_loss: %.4f - val_loss: %.4f - time: %.1fs",
            epoch,
            epochs,
            train_value,
            val_value,
            elapsed,
        )

        if val_value < best_val_loss:
            best_val_loss = val_value
            checkpoint_path = os.path.join(output_dir, "model_best.weights.h5")
            model.save_weights(checkpoint_path)
            logger.info("  New best model saved (val_loss=%.4f)", val_value)

        logs = {"train_loss": train_value, "val_loss": val_value}
        for callback in callbacks:
            callback.on_epoch_end(epoch, logs=logs)

    history_path = os.path.join(output_dir, "training_history.json")
    with open(history_path, "w", encoding="utf-8") as history_file:
        json.dump(history, history_file, indent=2)

    logger.info("Training complete. Best val_loss: %.4f", best_val_loss)
    logger.info("History saved to %s", history_path)
    return history


if __name__ == "__main__":
    logger.info("Building SmartTireModel...")
    smart_model = SmartTireModel()
    outputs = smart_model.build_graph()
    logger.info("Model built successfully.")
    for key, value in outputs.items():
        logger.info("  %s: %s", key, value.shape)
    smart_model.summary()
