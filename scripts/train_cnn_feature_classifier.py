"""
Train a CNN feature classifier for tire condition.

This is a lightweight alternative to full CNN fine-tuning:
1. Use ImageNet-pretrained ResNet-18 as a frozen CNN feature extractor.
2. Train a scikit-learn logistic classifier on the extracted image features.
3. Save the classifier, metadata, and validation/test metrics.

Run from project root:
    .venv\\Scripts\\python.exe scripts\\train_cnn_feature_classifier.py --reuse-prepared
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import torch
from joblib import dump
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from torchvision.models import ResNet18_Weights, resnet18

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_and_train import prepare_features_for_training, set_seed

MODEL_DIR = ROOT / "ai_model" / "saved_models" / "cnn_feature_classifier"
CONDITION_LABELS = ["safe", "moderate", "replace"]
CONDITION_TO_ID = {label: index for index, label in enumerate(CONDITION_LABELS)}
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train frozen-ResNet CNN feature classifier")
    parser.add_argument("--reuse-prepared", action="store_true")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--center-crop-ratio", type=float, default=0.85)
    parser.add_argument("--c", type=float, default=0.1, help="LogisticRegression C value")
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def choose_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def resolve_image_path(row: pd.Series) -> Path | None:
    for column in ("dataset_front_path", "image_path", "front_image_path"):
        value = str(row.get(column, "") or "")
        if value and Path(value).is_file():
            return Path(value)
    return None


def center_crop(image: np.ndarray, ratio: float) -> np.ndarray:
    ratio = float(np.clip(ratio, 0.2, 1.0))
    if ratio >= 0.999:
        return image

    h, w = image.shape[:2]
    crop_w = max(1, int(round(w * ratio)))
    crop_h = max(1, int(round(h * ratio)))
    x1 = max(0, (w - crop_w) // 2)
    y1 = max(0, (h - crop_h) // 2)
    return image[y1 : y1 + crop_h, x1 : x1 + crop_w]


def preprocess_image(image: np.ndarray, image_size: int, crop_ratio: float) -> np.ndarray:
    image = center_crop(image, crop_ratio)
    h, w = image.shape[:2]
    size = max(h, w)
    padded = np.zeros((size, size, 3), dtype=image.dtype)
    y = (size - h) // 2
    x = (size - w) // 2
    padded[y : y + h, x : x + w] = image
    resized = cv2.resize(padded, (image_size, image_size), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
    return np.transpose((rgb - mean) / std, (2, 0, 1)).astype(np.float32)


def build_feature_extractor(device: torch.device) -> torch.nn.Module:
    model = resnet18(weights=ResNet18_Weights.DEFAULT)
    model.fc = torch.nn.Identity()
    model.eval().to(device)
    return model


def extract_features(
    df: pd.DataFrame,
    model: torch.nn.Module,
    device: torch.device,
    image_size: int,
    crop_ratio: float,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    feature_batches: list[np.ndarray] = []
    labels: list[int] = []
    batch: list[np.ndarray] = []
    batch_labels: list[int] = []
    skipped = 0

    with torch.no_grad():
        for _, row in df.iterrows():
            image_path = resolve_image_path(row)
            if image_path is None:
                skipped += 1
                continue
            image = cv2.imread(str(image_path))
            if image is None:
                skipped += 1
                continue

            batch.append(preprocess_image(image, image_size, crop_ratio))
            batch_labels.append(CONDITION_TO_ID[str(row["condition"])])

            if len(batch) >= batch_size:
                tensor = torch.tensor(np.asarray(batch, dtype=np.float32), device=device)
                feature_batches.append(model(tensor).cpu().numpy())
                labels.extend(batch_labels)
                batch.clear()
                batch_labels.clear()

        if batch:
            tensor = torch.tensor(np.asarray(batch, dtype=np.float32), device=device)
            feature_batches.append(model(tensor).cpu().numpy())
            labels.extend(batch_labels)

    if not feature_batches:
        raise RuntimeError("No usable images found for feature extraction")

    return np.vstack(feature_batches), np.asarray(labels, dtype=np.int64), skipped


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    return {
        "condition_accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "condition_macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist(),
        "condition_labels": CONDITION_LABELS,
        "samples": int(len(y_true)),
    }


def main() -> None:
    args = parse_args()
    set_seed(SEED)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = prepare_features_for_training(reuse_prepared=args.reuse_prepared)
    df = df[df["has_image"]].reset_index(drop=True)
    train_df, temp_df = train_test_split(df, test_size=0.30, random_state=SEED, stratify=df["condition"])
    val_df, test_df = train_test_split(temp_df, test_size=0.50, random_state=SEED, stratify=temp_df["condition"])

    device = choose_device()
    extractor = build_feature_extractor(device)
    print(f"Using device: {device}")

    train_x, train_y, train_skipped = extract_features(
        train_df,
        extractor,
        device,
        args.image_size,
        args.center_crop_ratio,
        args.batch_size,
    )
    val_x, val_y, val_skipped = extract_features(
        val_df,
        extractor,
        device,
        args.image_size,
        args.center_crop_ratio,
        args.batch_size,
    )
    test_x, test_y, test_skipped = extract_features(
        test_df,
        extractor,
        device,
        args.image_size,
        args.center_crop_ratio,
        args.batch_size,
    )

    classifier = LogisticRegression(C=args.c, max_iter=2000, random_state=SEED)
    classifier.fit(train_x, train_y)

    val_metrics = metrics_dict(val_y, classifier.predict(val_x))
    test_metrics = metrics_dict(test_y, classifier.predict(test_x))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "resnet18_frozen_feature_logistic_classifier",
        "device": device.type,
        "training_config": {
            "image_size": args.image_size,
            "center_crop_ratio": args.center_crop_ratio,
            "c": args.c,
            "batch_size": args.batch_size,
        },
        "dataset": {
            "train_images": int(len(train_y)),
            "validation_images": int(len(val_y)),
            "test_images": int(len(test_y)),
            "skipped": {
                "train": int(train_skipped),
                "validation": int(val_skipped),
                "test": int(test_skipped),
            },
        },
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }

    dump(classifier, MODEL_DIR / "classifier.joblib")
    (MODEL_DIR / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
