"""
Train a compact Keras CNN for tire analysis and export to TFLite.
Produces model_best.h5 used by export_model.py.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IMAGE_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 15
FEATURE_COLUMNS = ["tread_1", "tread_2", "tread_3", "tread_4", "tread_average"]
CONDITION_LABELS = ["safe", "moderate", "replace"]


def parse_args():
    parser = argparse.ArgumentParser(description="Train Keras model and export to TFLite")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--quick", action="store_true", help="Quick test with few samples")
    return parser.parse_args()


def build_model():
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
        pooling="avg",
    )
    base.trainable = False
    inputs = tf.keras.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = tf.keras.layers.Rescaling(scale=1.0 / 127.5, offset=-1.0, name="preprocess")(inputs)
    x = base(x, training=False)
    x = tf.keras.layers.Dropout(0.3)(x)
    condition = tf.keras.layers.Dense(3, activation="softmax", name="condition")(x)
    health = tf.keras.layers.Dense(1, activation="sigmoid", name="health")(x)
    life = tf.keras.layers.Dense(1, activation="sigmoid", name="remaining_life")(x)
    model = tf.keras.Model(inputs=inputs, outputs=[condition, health, life])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-4),
        loss={
            "condition": "sparse_categorical_crossentropy",
            "health": "mse",
            "remaining_life": "mse",
        },
        loss_weights={"condition": 1.0, "health": 0.5, "remaining_life": 0.3},
        metrics={"condition": "accuracy"},
    )
    return model


def load_data(split_dir: Path, max_samples=None):
    csv_path = split_dir / "labels.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    has_img = df[df["has_image"]].copy()
    if max_samples:
        has_img = has_img.sample(min(max_samples, len(has_img)), random_state=42)
    images, conditions, healths, lives = [], [], [], []
    for _, row in has_img.iterrows():
        img_path = None
        for col in ("dataset_front_path", "front_image_path", "image_path"):
            val = row.get(col)
            if val and Path(str(val)).is_file():
                img_path = str(val)
                break
        if img_path is None:
            abs_path = ROOT / "dataset" / "images" / "front_view" / Path(str(row["image_id"]))
            if abs_path.is_file():
                img_path = str(abs_path)
            else:
                continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
        images.append(img.astype(np.float32))
        conditions.append(int(row["condition_id"]))
        healths.append(float(row["health_norm"]))
        lives.append(float(row["remaining_life_norm"]))
    if not images:
        return None
    return (
        np.array(images),
        np.array(conditions),
        np.array(healths, dtype=np.float32),
        np.array(lives, dtype=np.float32),
    )


def main():
    args = parse_args()
    splits_dir = ROOT / "dataset" / "splits"
    max_s = 50 if args.quick else None
    train_data = load_data(splits_dir / "train", max_samples=max_s)
    val_data = load_data(splits_dir / "validation", max_samples=max_s)
    if train_data is None:
        print("No training data found. Check dataset/splits/train/labels.csv")
        sys.exit(1)
    X_train, y_cond, y_health, y_life = train_data
    print(f"Training samples: {len(X_train)}")
    if val_data:
        X_val, yv_cond, yv_health, yv_life = val_data
        print(f"Validation samples: {len(X_val)}")
    else:
        X_val, yv_cond, yv_health, yv_life = None, None, None, None
    model = build_model()
    model.summary()
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(ROOT / "ai_model" / "saved_models" / "model_best.weights.h5"),
            save_weights_only=True,
            save_best_only=True,
            monitor="val_loss" if val_data else "loss",
        ),
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
    ]
    val_data_tuple = (X_val, {"condition": yv_cond, "health": yv_health, "remaining_life": yv_life}) if val_data else None
    model.fit(
        X_train,
        {"condition": y_cond, "health": y_health, "remaining_life": y_life},
        validation_data=val_data_tuple,
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        verbose=1,
    )
    h5_path = ROOT / "ai_model" / "saved_models" / "model_best.h5"
    model.save(str(h5_path))
    print(f"Model saved to {h5_path}")


if __name__ == "__main__":
    main()
