"""
ANN Prediction Head — Final prediction layers for Smart Tire Analyzer.
Takes fused multi-modal features and produces 4 outputs:
  1. Tread depth (regression) — average mm
  2. Tire health score (regression) — 0 to 10
  3. Remaining life (regression) — km or days
  4. Wear pattern (classification) — 6 classes
"""

import tensorflow as tf
from tensorflow.keras import layers, Model
from typing import Dict, Tuple


WEAR_CLASSES = 6  # center, edge, patchy, uniform, one-side, cupping

# Regression output ranges for interpretation
TREAD_MAX_MM = 12.0
HEALTH_SCORE_MAX = 10.0
MAX_REMAINING_KM = 80000.0


class TreadDepthHead(layers.Layer):
    """
    Regression head for predicting all 4 individual tread depths + average.
    Uses a shared backbone then splits into 5 outputs.
    """

    def __init__(self, dropout_rate: float = 0.2, **kwargs):
        super().__init__(**kwargs)
        self.shared = tf.keras.Sequential([
            layers.Dense(256, activation="relu"),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate),
            layers.Dense(128, activation="relu"),
            layers.BatchNormalization(),
        ], name="tread_shared")

        # Individual tread outputs (T1-T4)
        self.t1_out = layers.Dense(1, activation="sigmoid", name="tread_1")
        self.t2_out = layers.Dense(1, activation="sigmoid", name="tread_2")
        self.t3_out = layers.Dense(1, activation="sigmoid", name="tread_3")
        self.t4_out = layers.Dense(1, activation="sigmoid", name="tread_4")

    def call(self, x: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Returns: (batch, 4) — individual tread depths normalized [0, 1]
        Multiply by TREAD_MAX_MM for mm values.
        """
        shared = self.shared(x, training=training)
        t1 = self.t1_out(shared)
        t2 = self.t2_out(shared)
        t3 = self.t3_out(shared)
        t4 = self.t4_out(shared)
        return tf.concat([t1, t2, t3, t4], axis=-1)  # (batch, 4)

    def get_config(self):
        return super().get_config()


class HealthScoreHead(layers.Layer):
    """
    Regression head for tire health score (0–10).
    Uses uncertainty estimation with Monte Carlo dropout.
    """

    def __init__(self, dropout_rate: float = 0.3, **kwargs):
        super().__init__(**kwargs)
        self.d1 = layers.Dense(128, activation="relu", name="health_d1")
        self.bn1 = layers.BatchNormalization(name="health_bn1")
        self.drop = layers.Dropout(dropout_rate, name="health_drop")
        self.d2 = layers.Dense(64, activation="relu", name="health_d2")
        self.out = layers.Dense(1, activation="sigmoid", name="health_score")

    def call(self, x: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Returns: (batch, 1) — health score normalized [0, 1]
        Multiply by HEALTH_SCORE_MAX for 0–10 scale.
        """
        x = self.d1(x)
        x = self.bn1(x, training=training)
        x = self.drop(x, training=training)  # Keep active for MC dropout
        x = self.d2(x)
        return self.out(x)

    def monte_carlo_estimate(
        self,
        x: tf.Tensor,
        n_samples: int = 20,
    ) -> Tuple[tf.Tensor, tf.Tensor]:
        """
        MC Dropout uncertainty estimation.
        Returns (mean_prediction, std_uncertainty).
        """
        predictions = [self.call(x, training=True) for _ in range(n_samples)]
        stacked = tf.stack(predictions, axis=0)  # (n_samples, batch, 1)
        mean = tf.reduce_mean(stacked, axis=0)
        std = tf.math.reduce_std(stacked, axis=0)
        return mean, std

    def get_config(self):
        return super().get_config()


class RemainingLifeHead(layers.Layer):
    """
    Regression head for remaining tire life in km.
    Combines predicted tread depth with wear velocity features.
    """

    def __init__(self, dropout_rate: float = 0.2, **kwargs):
        super().__init__(**kwargs)
        self.d1 = layers.Dense(128, activation="relu", name="life_d1")
        self.bn = layers.BatchNormalization(name="life_bn")
        self.drop = layers.Dropout(dropout_rate, name="life_drop")
        self.d2 = layers.Dense(64, activation="relu", name="life_d2")
        self.out = layers.Dense(1, activation="sigmoid", name="remaining_life")

    def call(self, x: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Returns: (batch, 1) — remaining life normalized [0, 1]
        Multiply by MAX_REMAINING_KM for distance in km.
        """
        x = self.d1(x)
        x = self.bn(x, training=training)
        x = self.drop(x, training=training)
        x = self.d2(x)
        return self.out(x)

    def get_config(self):
        return super().get_config()


class WearPatternHead(layers.Layer):
    """
    Classification head for wear pattern detection.
    6 classes: center, edge, patchy, uniform, one-side, cupping.
    """

    def __init__(
        self,
        num_classes: int = WEAR_CLASSES,
        dropout_rate: float = 0.3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_classes = num_classes
        self.d1 = layers.Dense(256, activation="relu", name="wear_d1")
        self.bn1 = layers.BatchNormalization(name="wear_bn1")
        self.drop1 = layers.Dropout(dropout_rate, name="wear_drop1")
        self.d2 = layers.Dense(128, activation="relu", name="wear_d2")
        self.bn2 = layers.BatchNormalization(name="wear_bn2")
        self.drop2 = layers.Dropout(dropout_rate, name="wear_drop2")
        self.out = layers.Dense(num_classes, activation="softmax", name="wear_pattern")

    def call(self, x: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Returns: (batch, num_classes) — softmax probabilities
        """
        x = self.d1(x)
        x = self.bn1(x, training=training)
        x = self.drop1(x, training=training)
        x = self.d2(x)
        x = self.bn2(x, training=training)
        x = self.drop2(x, training=training)
        return self.out(x)

    def get_config(self):
        config = super().get_config()
        config.update({"num_classes": self.num_classes})
        return config


def build_prediction_head(
    fused_dim: int = 512,
    dropout_rate: float = 0.25,
) -> Model:
    """
    Build the complete ANN prediction head with 4 output branches.

    Input:
        fused_features: (batch, fused_dim) — from fusion layer

    Outputs (dict):
        tread_depths:   (batch, 4)  — T1-T4 normalized
        health_score:   (batch, 1)  — normalized 0-1
        remaining_life: (batch, 1)  — normalized 0-1
        wear_pattern:   (batch, 6)  — softmax probabilities
    """
    inputs = layers.Input(shape=(fused_dim,), name="fused_input")

    # Shared backbone before branching
    x = layers.Dense(512, activation="relu", name="shared_d1")(inputs)
    x = layers.BatchNormalization(name="shared_bn1")(x)
    x = layers.Dropout(dropout_rate, name="shared_drop1")(x)
    x = layers.Dense(256, activation="relu", name="shared_d2")(x)
    x = layers.BatchNormalization(name="shared_bn2")(x)

    # 4 separate prediction heads
    tread_head = TreadDepthHead(dropout_rate=dropout_rate, name="tread_head")
    health_head = HealthScoreHead(dropout_rate=dropout_rate, name="health_head")
    life_head = RemainingLifeHead(dropout_rate=dropout_rate, name="life_head")
    wear_head = WearPatternHead(dropout_rate=dropout_rate, name="wear_head")

    tread_out = tread_head(x)
    health_out = health_head(x)
    life_out = life_head(x)
    wear_out = wear_head(x)

    model = Model(
        inputs=inputs,
        outputs={
            "tread_depths": tread_out,
            "health_score": health_out,
            "remaining_life": life_out,
            "wear_pattern": wear_out,
        },
        name="prediction_head",
    )
    return model


if __name__ == "__main__":
    model = build_prediction_head()
    model.summary()
    dummy = tf.random.normal((4, 512))
    out = model(dummy, training=False)
    for k, v in out.items():
        print(f"{k}: {v.shape}")
