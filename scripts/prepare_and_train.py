"""
End-to-end preprocessing and training pipeline for Smart Tire Analyzer.

This script:
1. Loads the raw spreadsheet into ``dataset/processed/labels.csv``
2. Cleans and enriches the dataset
3. Matches tread images to labeled rows
4. Creates train / validation / test splits
5. Trains three models:
   - ANN (tabular tread features)
   - RNN (tread sequence features)
   - CNN (image-based)
6. Evaluates each model on validation and test splits
7. Writes a model registry and refreshes the runtime ANN weights

Run from project root:
    .venv\\Scripts\\python scripts\\prepare_and_train.py
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import random
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_model.cnn.preprocessing import run_preprocessing_pipeline
from ai_model.rnn.sequence_builder import build_tread_sequence
from ai_model.tabular_model import SmartTireTabular
from scripts.prepare_dataset import DatasetPaths, prepare_dataset

logging.getLogger("ai_model.cnn.preprocessing").setLevel(logging.ERROR)

DATASET_DIR = ROOT / "dataset"
RAW_DIR = DATASET_DIR / "raw"
SPREADSHEET_DIR = RAW_DIR / "spreadsheet"
TREAD_IMAGES_DIR = RAW_DIR / "tread_images"
PROCESSED_DIR = DATASET_DIR / "processed"
SPLITS_DIR = DATASET_DIR / "splits"
MODEL_DIR = ROOT / "ai_model" / "saved_models"

LABELS_CSV = PROCESSED_DIR / "labels.csv"
CLEANED_CSV = PROCESSED_DIR / "cleaned_dataset.csv"
FEATURES_CSV = PROCESSED_DIR / "features.csv"
REGISTRY_JSON = MODEL_DIR / "model_registry.json"
METADATA_JSON = MODEL_DIR / "model_metadata.json"
ANN_BEST_PATH = MODEL_DIR / "smart_tire_tabular_best.pt"
ANN_FINAL_PATH = MODEL_DIR / "smart_tire_tabular_final.pt"
ANN_HISTORY_PATH = MODEL_DIR / "training_history.json"

FEATURE_COLUMNS = ["tread_1", "tread_2", "tread_3", "tread_4", "tread_average"]
FEATURE_MAX = np.array([12.0, 12.0, 12.0, 12.0, 12.0], dtype=np.float32)
CONDITION_TO_ID = {"safe": 0, "moderate": 1, "replace": 2}
CONDITION_LABELS = ["safe", "moderate", "replace"]
WEAR_TO_ID = {
    "center_wear": 0,
    "edge_wear": 1,
    "uneven_wear": 2,
    "even": 3,
    "one_sided_wear": 4,
    "critical_wear": 5,
}
WEAR_LABELS = [
    "center_wear",
    "edge_wear",
    "uneven_wear",
    "even",
    "one_sided_wear",
    "critical_wear",
]
SAFE_TIRE_LIFE_KM = 80_000.0
MAX_HEALTH_SCORE = 10.0
SEED = 42

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("prepare_and_train")


BRAND_MAP = {
    "apollo": "Apollo",
    "applo": "Apollo",
    "mrf": "MRF",
    "bridgestone": "Bridgestone",
    "goodyear": "Goodyear",
    "goodyer": "Goodyear",
    "good year": "Goodyear",
    "ceat": "CEAT",
    "jk tyre": "JK Tyre",
    "jktyre": "JK Tyre",
    "yokohama": "Yokohama",
    "yokohamma": "Yokohama",
    "michelin": "Michelin",
    "michilen": "Michelin",
    "kelly": "Kelly",
    "firestone": "Firestone",
    "continental": "Continental",
    "pirelli": "Pirelli",
    "dunlop": "Dunlop",
    "maxtrek": "Maxtrek",
    "toyo": "Toyo",
}


@dataclass
class TrainConfig:
    ann_epochs: int = 18
    rnn_epochs: int = 18
    cnn_epochs: int = 8
    ann_batch_size: int = 64
    rnn_batch_size: int = 64
    cnn_batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-3
    patience: int = 4
    cnn_image_size: int = 128
    cnn_architecture: str = "compact"
    cnn_pretrained: bool = False
    cnn_augment_copies: int = 0
    cnn_balanced_sampler: bool = False
    cnn_condition_loss_weight: float = 1.0
    cnn_regression_loss_weight: float = 0.5
    cnn_include_edge_channel: bool = True
    cnn_center_crop_ratio: float = 1.0
    cnn_freeze_encoder: bool = False
    cnn_raw_rgb: bool = False
    max_samples: int | None = None
    reuse_prepared: bool = False


@dataclass
class TrainingArtifact:
    name: str
    best_weights: Path
    history_path: Path
    val_metrics_path: Path
    test_metrics_path: Path
    history: dict[str, list[float]]
    val_metrics: dict[str, Any]
    test_metrics: dict[str, Any]


class SequenceConditionModel(nn.Module):
    """BiLSTM model trained on the 4-step tread sequence."""

    def __init__(self, input_dim: int = 7) -> None:
        super().__init__()
        self.rnn = nn.LSTM(
            input_size=input_dim,
            hidden_size=64,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.2,
        )
        self.backbone = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 96),
            nn.ReLU(),
        )
        self.condition_head = nn.Linear(96, 3)
        self.health_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.life_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sequence, _ = self.rnn(x)
        features = sequence[:, -1, :]
        features = self.backbone(features)
        return (
            self.condition_head(features),
            self.health_head(features).squeeze(1),
            self.life_head(features).squeeze(1),
        )


class ImageConditionModel(nn.Module):
    """Compact CNN for tread image classification/regression."""

    def __init__(self, in_channels: int = 4) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.backbone = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 96),
            nn.ReLU(),
        )
        self.condition_head = nn.Linear(96, 3)
        self.health_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.life_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.encoder(x)
        features = self.backbone(features)
        return (
            self.condition_head(features),
            self.health_head(features).squeeze(1),
            self.life_head(features).squeeze(1),
        )


class DenseNetImageConditionModel(nn.Module):
    """DenseNet-121 image model with the same multi-task heads as the compact CNN."""

    def __init__(self, in_channels: int = 4, pretrained: bool = False) -> None:
        super().__init__()
        try:
            from torchvision.models import DenseNet121_Weights, densenet121
        except ImportError as exc:
            raise RuntimeError(
                "DenseNet CNN requires torchvision. Install it with: "
                "python -m pip install torchvision --index-url https://download.pytorch.org/whl/cu130"
            ) from exc

        weights = DenseNet121_Weights.DEFAULT if pretrained else None
        self.encoder = densenet121(weights=weights)
        self._adapt_first_convolution(in_channels)

        feature_dim = self.encoder.classifier.in_features
        self.encoder.classifier = nn.Identity()
        self.backbone = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.35),
            nn.Linear(256, 96),
            nn.ReLU(),
        )
        self.condition_head = nn.Linear(96, 3)
        self.health_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.life_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

    def _adapt_first_convolution(self, in_channels: int) -> None:
        old_conv = self.encoder.features.conv0
        if old_conv.in_channels == in_channels:
            return

        new_conv = nn.Conv2d(
            in_channels=in_channels,
            out_channels=old_conv.out_channels,
            kernel_size=old_conv.kernel_size,
            stride=old_conv.stride,
            padding=old_conv.padding,
            bias=old_conv.bias is not None,
        )
        with torch.no_grad():
            if old_conv.weight.shape[1] == 3:
                copied_channels = min(in_channels, 3)
                new_conv.weight[:, :copied_channels] = old_conv.weight[:, :copied_channels]
                if in_channels > 3:
                    extra = old_conv.weight.mean(dim=1, keepdim=True)
                    new_conv.weight[:, 3:] = extra.repeat(1, in_channels - 3, 1, 1)
            else:
                nn.init.kaiming_normal_(new_conv.weight, mode="fan_out", nonlinearity="relu")
            if old_conv.bias is not None and new_conv.bias is not None:
                new_conv.bias.copy_(old_conv.bias)

        self.encoder.features.conv0 = new_conv

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.encoder(x)
        features = self.backbone(features)
        return (
            self.condition_head(features),
            self.health_head(features).squeeze(1),
            self.life_head(features).squeeze(1),
        )


class ResNetImageConditionModel(nn.Module):
    """ResNet-18 image model with the same multi-task heads as the compact CNN."""

    def __init__(self, in_channels: int = 3, pretrained: bool = False) -> None:
        super().__init__()
        try:
            from torchvision.models import ResNet18_Weights, resnet18
        except ImportError as exc:
            raise RuntimeError(
                "ResNet CNN requires torchvision. Install it with: "
                "python -m pip install torchvision --index-url https://download.pytorch.org/whl/cu130"
            ) from exc

        weights = ResNet18_Weights.DEFAULT if pretrained else None
        self.encoder = resnet18(weights=weights)
        self._adapt_first_convolution(in_channels)

        feature_dim = self.encoder.fc.in_features
        self.encoder.fc = nn.Identity()
        self.backbone = nn.Sequential(
            nn.Linear(feature_dim, 192),
            nn.ReLU(),
            nn.Dropout(0.35),
            nn.Linear(192, 96),
            nn.ReLU(),
        )
        self.condition_head = nn.Linear(96, 3)
        self.health_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.life_head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

    def _adapt_first_convolution(self, in_channels: int) -> None:
        old_conv = self.encoder.conv1
        if old_conv.in_channels == in_channels:
            return

        new_conv = nn.Conv2d(
            in_channels=in_channels,
            out_channels=old_conv.out_channels,
            kernel_size=old_conv.kernel_size,
            stride=old_conv.stride,
            padding=old_conv.padding,
            bias=old_conv.bias is not None,
        )
        with torch.no_grad():
            if old_conv.weight.shape[1] == 3:
                copied_channels = min(in_channels, 3)
                new_conv.weight[:, :copied_channels] = old_conv.weight[:, :copied_channels]
                if in_channels > 3:
                    extra = old_conv.weight.mean(dim=1, keepdim=True)
                    new_conv.weight[:, 3:] = extra.repeat(1, in_channels - 3, 1, 1)
            else:
                nn.init.kaiming_normal_(new_conv.weight, mode="fan_out", nonlinearity="relu")
            if old_conv.bias is not None and new_conv.bias is not None:
                new_conv.bias.copy_(old_conv.bias)

        self.encoder.conv1 = new_conv

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.encoder(x)
        features = self.backbone(features)
        return (
            self.condition_head(features),
            self.health_head(features).squeeze(1),
            self.life_head(features).squeeze(1),
        )


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _normalize_filename(text: str) -> str:
    normalized = str(text).strip().lower()
    normalized = normalized.replace(".jpeg", ".jpg").replace(".heic", ".jpg")
    normalized = normalized.replace("copy of ", "")
    normalized = normalized.replace(" - viren viren", "")
    normalized = normalized.replace(" - ubaid elahi baba", "")
    normalized = re.sub(r"\[\d+\]", "", normalized)
    normalized = normalized.replace("(1)", "").replace("(2)", "")
    normalized = normalized.replace(".jpg", "")
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    return normalized


def _normalise_brand(name: object) -> str:
    if pd.isna(name):
        return "Unknown"
    raw = str(name).strip()
    return BRAND_MAP.get(raw.lower(), raw.title())


def _tread_to_condition(avg_tread_mm: float) -> str:
    if avg_tread_mm >= 4.0:
        return "safe"
    if avg_tread_mm >= 1.6:
        return "moderate"
    return "replace"


def _tread_to_wear(row: pd.Series) -> str:
    tread_values = [float(row["tread_1"]), float(row["tread_2"]), float(row["tread_3"]), float(row["tread_4"])]
    tread_range = max(tread_values) - min(tread_values)
    center = float(np.mean([tread_values[1], tread_values[2]]))
    edges = float(np.mean([tread_values[0], tread_values[3]]))

    if tread_range < 0.5:
        return "even"
    if center > edges + 0.5:
        return "center_wear"
    if edges > center + 0.5:
        return "edge_wear"
    if abs(tread_values[0] - tread_values[3]) > 1.0:
        return "one_sided_wear"
    if tread_range > 2.0:
        return "critical_wear"
    return "uneven_wear"


def _ensure_runtime_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _find_spreadsheet() -> Path:
    xlsx_files = sorted(SPREADSHEET_DIR.glob("*.xlsx"))
    if not xlsx_files:
        raise FileNotFoundError(f"No spreadsheet found in {SPREADSHEET_DIR}")
    return xlsx_files[0]


def load_excel_to_csv() -> pd.DataFrame:
    spreadsheet = _find_spreadsheet()
    logger.info("Loading spreadsheet: %s", spreadsheet.name)
    try:
        dataframe = pd.read_excel(spreadsheet)
    except ImportError:
        if LABELS_CSV.exists():
            logger.warning("openpyxl is unavailable; falling back to existing %s", LABELS_CSV)
            return pd.read_csv(LABELS_CSV)
        raise
    logger.info("Loaded spreadsheet with %d rows and %d columns", len(dataframe), len(dataframe.columns))

    rename_map = {
        "Front Profile": "image_id",
        "Tread 1": "tread_1",
        "Tread 2": "tread_2",
        "Tread 3": "tread_3",
        "Tread 4": "tread_4",
        "Average form": "tread_average",
        "Company name": "brand",
        "model": "tire_model",
        "Tire Size": "tire_size",
        "Company Manufacture": "manufacture_country",
        "TUBE/TUBELESS": "tube_type",
    }
    dataframe = dataframe.rename(columns={old: new for old, new in rename_map.items() if old in dataframe.columns})

    keep_columns = [
        "image_id",
        "tread_1",
        "tread_2",
        "tread_3",
        "tread_4",
        "tread_average",
        "brand",
        "tire_model",
        "tire_size",
    ]
    dataframe = dataframe[[column for column in keep_columns if column in dataframe.columns]]
    dataframe.to_csv(LABELS_CSV, index=False)
    logger.info("Saved raw labels to %s", LABELS_CSV)
    return dataframe


def clean_and_enrich(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning and enriching dataset")
    cleaned = df.copy()
    cleaned = cleaned.dropna(subset=["image_id"]).copy()
    cleaned["image_id"] = cleaned["image_id"].astype(str).str.strip()
    cleaned = cleaned.drop_duplicates(subset=["image_id"]).reset_index(drop=True)

    for column in FEATURE_COLUMNS[:-1]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    tread_4_missing = cleaned["tread_4"].isna() | (cleaned["tread_4"] == 0.0)
    cleaned.loc[tread_4_missing, "tread_4"] = cleaned.loc[tread_4_missing, ["tread_1", "tread_2", "tread_3"]].mean(axis=1)

    for column in FEATURE_COLUMNS[:-1]:
        column_missing = cleaned[column].isna()
        if column_missing.any():
            peers = [value for value in FEATURE_COLUMNS[:-1] if value != column]
            cleaned.loc[column_missing, column] = cleaned.loc[column_missing, peers].mean(axis=1)

    for column in FEATURE_COLUMNS[:-1]:
        cleaned[column] = cleaned[column].clip(0.0, 12.0)

    cleaned["tread_average"] = cleaned[FEATURE_COLUMNS[:-1]].mean(axis=1)
    cleaned["brand"] = cleaned["brand"].apply(_normalise_brand)
    cleaned["condition"] = cleaned["tread_average"].apply(_tread_to_condition)
    cleaned["condition_id"] = cleaned["condition"].map(CONDITION_TO_ID).astype(int)
    cleaned["wear_pattern"] = cleaned.apply(_tread_to_wear, axis=1)
    cleaned["wear_class_6"] = cleaned["wear_pattern"].map(WEAR_TO_ID).fillna(2).astype(int)
    cleaned["health_score"] = ((cleaned["tread_average"] / 12.0) * 10.0).clip(0.0, 10.0).round(2)
    cleaned["health_norm"] = (cleaned["health_score"] / MAX_HEALTH_SCORE).astype(np.float32)
    cleaned["remaining_life_km"] = (
        ((cleaned["tread_average"] - 1.6) / (12.0 - 1.6) * SAFE_TIRE_LIFE_KM).clip(0.0, SAFE_TIRE_LIFE_KM).round(0)
    )
    cleaned["remaining_life_norm"] = (cleaned["remaining_life_km"] / SAFE_TIRE_LIFE_KM).astype(np.float32)
    cleaned["manufacture_year"] = cleaned.get("manufacture_year", 2022)
    cleaned.to_csv(CLEANED_CSV, index=False)

    logger.info("Cleaned dataset saved to %s", CLEANED_CSV)
    logger.info(
        "Condition distribution: %s",
        cleaned["condition"].value_counts().to_dict(),
    )
    logger.info(
        "Wear distribution: %s",
        cleaned["wear_pattern"].value_counts().to_dict(),
    )
    return cleaned


def build_image_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for image_path in TREAD_IMAGES_DIR.iterdir():
        if not image_path.is_file():
            continue
        index[image_path.name.lower()] = image_path
        index[_normalize_filename(image_path.name)] = image_path
    return index


def attach_image_paths(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Matching tread images to cleaned rows")
    image_index = build_image_index()
    enriched = df.copy()
    image_paths: list[str | None] = []
    for image_id in enriched["image_id"]:
        exact = image_index.get(str(image_id).lower())
        if exact is None:
            exact = image_index.get(_normalize_filename(str(image_id)))
        image_paths.append(str(exact) if exact is not None else None)

    enriched["image_path"] = image_paths
    enriched["has_image"] = enriched["image_path"].notna()
    enriched["feature_tread_spread"] = (enriched["tread_1"] - enriched["tread_4"]).abs().astype(np.float32)
    enriched["feature_center_edge_gap"] = (
        ((enriched["tread_2"] + enriched["tread_3"]) / 2.0) - ((enriched["tread_1"] + enriched["tread_4"]) / 2.0)
    ).astype(np.float32)
    enriched.to_csv(FEATURES_CSV, index=False)

    logger.info(
        "Matched %d / %d labeled rows to tread images",
        int(enriched["has_image"].sum()),
        len(enriched),
    )
    logger.info("Feature manifest saved to %s", FEATURES_CSV)
    return enriched


def prepare_features_for_training(reuse_prepared: bool = False) -> pd.DataFrame:
    """Build generated dataset artifacts, then load the prepared feature table."""
    if reuse_prepared and FEATURES_CSV.exists():
        logger.info("Reusing prepared feature table at %s", FEATURES_CSV)
    else:
        logger.info("Preparing dataset artifacts before training")
        manifest = prepare_dataset(paths=DatasetPaths(root=DATASET_DIR))
        logger.info(
            "Prepared %d rows with %d matched front images",
            manifest["row_counts"]["processed_rows"],
            manifest["image_matching"]["front_matched"],
        )
    if not FEATURES_CSV.exists():
        raise FileNotFoundError(f"Prepared feature table not found at {FEATURES_CSV}")

    features = pd.read_csv(FEATURES_CSV)
    required_columns = set(FEATURE_COLUMNS) | {
        "condition_id",
        "health_norm",
        "remaining_life_norm",
        "has_image",
    }
    missing = sorted(required_columns.difference(features.columns))
    if missing:
        raise ValueError(f"Prepared feature table is missing required columns: {missing}")
    return features


def limit_training_rows(df: pd.DataFrame, max_samples: int | None) -> pd.DataFrame:
    """Return a small stratified subset for smoke checks when requested."""
    if max_samples is None or max_samples <= 0 or len(df) <= max_samples:
        return df

    parts: list[pd.DataFrame] = []
    for _, group in df.groupby("condition", sort=False):
        proportional = int(round(max_samples * (len(group) / len(df))))
        sample_count = max(1, min(len(group), proportional))
        parts.append(group.sample(n=sample_count, random_state=SEED))

    limited = pd.concat(parts).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    if len(limited) > max_samples:
        limited = limited.sample(n=max_samples, random_state=SEED).reset_index(drop=True)
    logger.info(
        "Using %d/%d prepared rows for this training run (--max-samples)",
        len(limited),
        len(df),
    )
    return limited


def split_dataset(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    logger.info("Creating train / validation / test splits")
    stratify = df["condition"] if df["condition"].value_counts().min() >= 2 else None
    try:
        train_df, temp_df = train_test_split(
            df,
            test_size=0.30,
            random_state=SEED,
            stratify=stratify,
        )
        temp_stratify = temp_df["condition"] if temp_df["condition"].value_counts().min() >= 2 else None
        val_df, test_df = train_test_split(
            temp_df,
            test_size=0.50,
            random_state=SEED,
            stratify=temp_stratify,
        )
    except ValueError:
        shuffled = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
        train_end = max(1, int(len(shuffled) * 0.70))
        val_end = min(len(shuffled), train_end + max(1, int(len(shuffled) * 0.15)))
        train_df = shuffled.iloc[:train_end]
        val_df = shuffled.iloc[train_end:val_end]
        test_df = shuffled.iloc[val_end:]

    splits = {"train": train_df.reset_index(drop=True), "validation": val_df.reset_index(drop=True), "test": test_df.reset_index(drop=True)}
    for split_name, split_df in splits.items():
        split_dir = SPLITS_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        split_df.to_csv(split_dir / "labels.csv", index=False)
        logger.info(
            "%s split: %d rows (%d with images)",
            split_name,
            len(split_df),
            int(split_df["has_image"].sum()),
        )
    return splits


def _build_tabular_tensors(df: pd.DataFrame) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    features = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32) / FEATURE_MAX
    condition = df["condition_id"].to_numpy(dtype=np.int64)
    health = df["health_norm"].to_numpy(dtype=np.float32)
    life = df["remaining_life_norm"].to_numpy(dtype=np.float32)
    return (
        torch.from_numpy(features),
        torch.from_numpy(condition),
        torch.from_numpy(health),
        torch.from_numpy(life),
    )


def _build_sequence_tensors(df: pd.DataFrame) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    sequences = []
    for row in df.itertuples(index=False):
        depths = [float(row.tread_1), float(row.tread_2), float(row.tread_3), float(row.tread_4)]
        sequences.append(build_tread_sequence(depths))

    sequence_array = np.asarray(sequences, dtype=np.float32)
    condition = df["condition_id"].to_numpy(dtype=np.int64)
    health = df["health_norm"].to_numpy(dtype=np.float32)
    life = df["remaining_life_norm"].to_numpy(dtype=np.float32)
    return (
        torch.from_numpy(sequence_array),
        torch.from_numpy(condition),
        torch.from_numpy(health),
        torch.from_numpy(life),
    )


def _build_image_tensors(
    df: pd.DataFrame,
    image_size: int,
    augment_copies: int = 0,
    include_edge_channel: bool = True,
    center_crop_ratio: float = 1.0,
    raw_rgb: bool = False,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, int]:
    images: list[np.ndarray] = []
    conditions: list[int] = []
    health_scores: list[float] = []
    remaining_life: list[float] = []
    skipped = 0

    image_rows = df[df["has_image"]].reset_index(drop=True)
    for row in image_rows.itertuples(index=False):
        image_path = None
        for attr in ("dataset_front_path", "image_path", "front_image_path"):
            value = str(getattr(row, attr, "") or "")
            if value and Path(value).is_file():
                image_path = Path(value)
                break
        if image_path is None:
            skipped += 1
            continue
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            skipped += 1
            continue
        image = _center_crop_image(image, center_crop_ratio)

        if raw_rgb:
            processed = _preprocess_raw_rgb(image, image_size)
        else:
            processed = run_preprocessing_pipeline(
                image,
                training=False,
                include_edge_channel=include_edge_channel,
                blur_threshold=0.0,
            )
        if processed is None:
            skipped += 1
            continue

        variants = [processed]
        for _ in range(max(0, augment_copies)):
            if raw_rgb:
                augmented = _augment_raw_rgb(image, image_size)
            else:
                augmented = run_preprocessing_pipeline(
                    image,
                    training=True,
                    include_edge_channel=include_edge_channel,
                    blur_threshold=0.0,
                )
            if augmented is not None:
                variants.append(augmented)

        for variant in variants:
            if variant.shape[0] != image_size or variant.shape[1] != image_size:
                variant = cv2.resize(variant, (image_size, image_size), interpolation=cv2.INTER_AREA)

            chw = np.transpose(variant.astype(np.float32), (2, 0, 1))
            images.append(chw)
            conditions.append(int(row.condition_id))
            health_scores.append(float(row.health_norm))
            remaining_life.append(float(row.remaining_life_norm))

    if not images:
        raise RuntimeError("No usable images remained after preprocessing")

    image_tensor = torch.from_numpy(np.asarray(images, dtype=np.float32))
    condition_tensor = torch.tensor(conditions, dtype=torch.int64)
    health_tensor = torch.tensor(health_scores, dtype=torch.float32)
    life_tensor = torch.tensor(remaining_life, dtype=torch.float32)
    return image_tensor, condition_tensor, health_tensor, life_tensor, skipped


def build_image_model(config: TrainConfig, in_channels: int) -> nn.Module:
    if config.cnn_architecture == "compact":
        model = ImageConditionModel(in_channels=in_channels)
    elif config.cnn_architecture == "densenet121":
        model = DenseNetImageConditionModel(in_channels=in_channels, pretrained=config.cnn_pretrained)
    elif config.cnn_architecture == "resnet18":
        model = ResNetImageConditionModel(in_channels=in_channels, pretrained=config.cnn_pretrained)
    else:
        raise ValueError(f"Unsupported CNN architecture: {config.cnn_architecture}")

    if config.cnn_freeze_encoder and hasattr(model, "encoder"):
        for parameter in model.encoder.parameters():
            parameter.requires_grad = False
    return model


def _center_crop_image(image: np.ndarray, crop_ratio: float) -> np.ndarray:
    ratio = float(np.clip(crop_ratio, 0.2, 1.0))
    if ratio >= 0.999:
        return image

    h, w = image.shape[:2]
    crop_w = max(1, int(round(w * ratio)))
    crop_h = max(1, int(round(h * ratio)))
    x1 = max(0, (w - crop_w) // 2)
    y1 = max(0, (h - crop_h) // 2)
    return image[y1 : y1 + crop_h, x1 : x1 + crop_w]


def _preprocess_raw_rgb(image: np.ndarray, image_size: int) -> np.ndarray:
    padded = _pad_to_square_local(image)
    resized = cv2.resize(padded, (image_size, image_size), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
    return ((rgb - mean) / std).astype(np.float32)


def _augment_raw_rgb(image: np.ndarray, image_size: int) -> np.ndarray:
    from ai_model.cnn.preprocessing import build_augmentation_pipeline

    padded = _pad_to_square_local(image)
    resized = cv2.resize(padded, (image_size, image_size), interpolation=cv2.INTER_AREA)
    augmented = build_augmentation_pipeline(training=True)(image=resized)["image"]
    return _preprocess_raw_rgb(augmented, image_size)


def _pad_to_square_local(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    size = max(h, w)
    padded = np.zeros((size, size, image.shape[2]), dtype=image.dtype)
    y = (size - h) // 2
    x = (size - w) // 2
    padded[y : y + h, x : x + w] = image
    return padded


def _build_loader(
    inputs: torch.Tensor,
    condition: torch.Tensor,
    health: torch.Tensor,
    life: torch.Tensor,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    dataset = TensorDataset(inputs, condition, health, life)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0, drop_last=False)


def _build_balanced_loader(
    inputs: torch.Tensor,
    condition: torch.Tensor,
    health: torch.Tensor,
    life: torch.Tensor,
    batch_size: int,
) -> DataLoader:
    dataset = TensorDataset(inputs, condition, health, life)
    labels = condition.numpy()
    counts = np.bincount(labels, minlength=len(CONDITION_LABELS)).astype(np.float32)
    counts[counts == 0.0] = 1.0
    sample_weights = torch.tensor(1.0 / counts[labels], dtype=torch.float32)
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )
    return DataLoader(dataset, batch_size=batch_size, sampler=sampler, num_workers=0, drop_last=False)


def _compute_class_weights(labels: torch.Tensor) -> torch.Tensor:
    counts = np.bincount(labels.numpy(), minlength=len(CONDITION_LABELS)).astype(np.float32)
    counts[counts == 0.0] = 1.0
    weights = counts.sum() / (len(CONDITION_LABELS) * counts)
    return torch.tensor(weights, dtype=torch.float32)


def _multitask_loss(
    logits: torch.Tensor,
    health_pred: torch.Tensor,
    life_pred: torch.Tensor,
    condition_true: torch.Tensor,
    health_true: torch.Tensor,
    life_true: torch.Tensor,
    ce_loss: nn.Module,
    reg_loss: nn.Module,
    condition_loss_weight: float = 1.0,
    health_loss_weight: float = 0.5,
    life_loss_weight: float = 0.5,
) -> torch.Tensor:
    loss_condition = ce_loss(logits, condition_true)
    loss_health = reg_loss(health_pred, health_true)
    loss_life = reg_loss(life_pred, life_true)
    return (
        (condition_loss_weight * loss_condition)
        + (health_loss_weight * loss_health)
        + (life_loss_weight * loss_life)
    )


def _evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    ce_loss: nn.Module,
    reg_loss: nn.Module,
    condition_loss_weight: float = 1.0,
    health_loss_weight: float = 0.5,
    life_loss_weight: float = 0.5,
) -> dict[str, Any]:
    model.eval()
    total_loss = 0.0
    y_true: list[int] = []
    y_pred: list[int] = []
    health_true_values: list[float] = []
    health_pred_values: list[float] = []
    life_true_values: list[float] = []
    life_pred_values: list[float] = []

    with torch.no_grad():
        for xb, condition_true, health_true, life_true in loader:
            xb = xb.to(device)
            condition_true = condition_true.to(device)
            health_true = health_true.to(device)
            life_true = life_true.to(device)

            logits, health_pred, life_pred = model(xb)
            loss = _multitask_loss(
                logits,
                health_pred,
                life_pred,
                condition_true,
                health_true,
                life_true,
                ce_loss,
                reg_loss,
                condition_loss_weight,
                health_loss_weight,
                life_loss_weight,
            )
            total_loss += float(loss.item())

            predicted_condition = logits.argmax(dim=1).cpu().numpy()
            y_pred.extend(predicted_condition.tolist())
            y_true.extend(condition_true.cpu().numpy().tolist())
            health_true_values.extend((health_true.cpu().numpy() * MAX_HEALTH_SCORE).tolist())
            health_pred_values.extend((health_pred.cpu().numpy() * MAX_HEALTH_SCORE).tolist())
            life_true_values.extend((life_true.cpu().numpy() * SAFE_TIRE_LIFE_KM).tolist())
            life_pred_values.extend((life_pred.cpu().numpy() * SAFE_TIRE_LIFE_KM).tolist())

    accuracy = accuracy_score(y_true, y_pred) if y_true else 0.0
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0) if y_true else 0.0
    confusion = confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist() if y_true else [[0, 0, 0]] * 3
    health_mae = float(np.mean(np.abs(np.asarray(health_true_values) - np.asarray(health_pred_values)))) if health_true_values else 0.0
    life_mae = float(np.mean(np.abs(np.asarray(life_true_values) - np.asarray(life_pred_values)))) if life_true_values else 0.0
    average_loss = total_loss / max(len(loader), 1)

    return {
        "loss": round(average_loss, 4),
        "condition_accuracy": round(float(accuracy), 4),
        "condition_macro_f1": round(float(macro_f1), 4),
        "health_mae": round(health_mae, 4),
        "remaining_life_mae_km": round(life_mae, 2),
        "confusion_matrix": confusion,
        "condition_labels": CONDITION_LABELS,
        "samples": len(y_true),
    }


def _train_model(
    name: str,
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    device: torch.device,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    patience: int,
    artifact_dir: Path,
    condition_loss_weight: float = 1.0,
    health_loss_weight: float = 0.5,
    life_loss_weight: float = 0.5,
    monitor_metric: str = "loss",
    monitor_mode: str = "min",
) -> TrainingArtifact:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    best_path = artifact_dir / f"{name}_best.pt"
    history_path = artifact_dir / "history.json"
    val_path = artifact_dir / "validation_metrics.json"
    test_path = artifact_dir / "test_metrics.json"

    model = model.to(device)
    class_weights = _compute_class_weights(train_loader.dataset.tensors[1]).to(device)
    ce_loss = nn.CrossEntropyLoss(weight=class_weights)
    reg_loss = nn.SmoothL1Loss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)

    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_loss": [],
        "val_condition_accuracy": [],
        "val_health_mae": [],
        "val_remaining_life_mae_km": [],
    }
    best_monitor_value = float("inf") if monitor_mode == "min" else -float("inf")
    bad_epochs = 0

    logger.info("Training %s on %s", name.upper(), device)

    def improved(value: float) -> bool:
        if monitor_mode == "max":
            return value > best_monitor_value
        return value < best_monitor_value

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0

        for xb, condition_true, health_true, life_true in train_loader:
            xb = xb.to(device)
            condition_true = condition_true.to(device)
            health_true = health_true.to(device)
            life_true = life_true.to(device)

            optimizer.zero_grad()
            logits, health_pred, life_pred = model(xb)
            loss = _multitask_loss(
                logits,
                health_pred,
                life_pred,
                condition_true,
                health_true,
                life_true,
                ce_loss,
                reg_loss,
                condition_loss_weight,
                health_loss_weight,
                life_loss_weight,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            running_loss += float(loss.item())

        train_loss = running_loss / max(len(train_loader), 1)
        val_metrics = _evaluate_model(
            model,
            val_loader,
            device,
            ce_loss,
            reg_loss,
            condition_loss_weight,
            health_loss_weight,
            life_loss_weight,
        )
        scheduler.step(val_metrics["loss"])

        history["train_loss"].append(round(train_loss, 4))
        history["val_loss"].append(val_metrics["loss"])
        history["val_condition_accuracy"].append(val_metrics["condition_accuracy"])
        history["val_health_mae"].append(val_metrics["health_mae"])
        history["val_remaining_life_mae_km"].append(val_metrics["remaining_life_mae_km"])

        logger.info(
            "%s epoch %02d/%02d - train_loss=%.4f val_loss=%.4f val_acc=%.3f health_mae=%.3f life_mae=%.2fkm",
            name.upper(),
            epoch,
            epochs,
            train_loss,
            val_metrics["loss"],
            val_metrics["condition_accuracy"],
            val_metrics["health_mae"],
            val_metrics["remaining_life_mae_km"],
        )

        monitor_value = float(val_metrics[monitor_metric])
        if improved(monitor_value):
            best_monitor_value = monitor_value
            bad_epochs = 0
            torch.save(model.state_dict(), best_path)
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                logger.info("%s early stopping at epoch %d", name.upper(), epoch)
                break

    if not best_path.exists():
        raise RuntimeError(f"Training for {name} did not produce weights")

    model.load_state_dict(torch.load(best_path, map_location=device))
    val_metrics = _evaluate_model(
        model,
        val_loader,
        device,
        ce_loss,
        reg_loss,
        condition_loss_weight,
        health_loss_weight,
        life_loss_weight,
    )
    test_metrics = _evaluate_model(
        model,
        test_loader,
        device,
        ce_loss,
        reg_loss,
        condition_loss_weight,
        health_loss_weight,
        life_loss_weight,
    )

    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    val_path.write_text(json.dumps(val_metrics, indent=2), encoding="utf-8")
    test_path.write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")

    return TrainingArtifact(
        name=name,
        best_weights=best_path,
        history_path=history_path,
        val_metrics_path=val_path,
        test_metrics_path=test_path,
        history=history,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
    )


def train_ann_model(
    splits: dict[str, pd.DataFrame],
    config: TrainConfig,
    device: torch.device,
) -> TrainingArtifact:
    train_inputs, train_condition, train_health, train_life = _build_tabular_tensors(splits["train"])
    val_inputs, val_condition, val_health, val_life = _build_tabular_tensors(splits["validation"])
    test_inputs, test_condition, test_health, test_life = _build_tabular_tensors(splits["test"])

    train_loader = _build_loader(train_inputs, train_condition, train_health, train_life, config.ann_batch_size, True)
    val_loader = _build_loader(val_inputs, val_condition, val_health, val_life, config.ann_batch_size, False)
    test_loader = _build_loader(test_inputs, test_condition, test_health, test_life, config.ann_batch_size, False)

    model = SmartTireTabular(in_dim=len(FEATURE_COLUMNS))
    artifact = _train_model(
        name="ann",
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        device=device,
        epochs=config.ann_epochs,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        patience=config.patience,
        artifact_dir=MODEL_DIR / "ann",
    )

    shutil.copy2(artifact.best_weights, ANN_BEST_PATH)
    shutil.copy2(artifact.history_path, ANN_HISTORY_PATH)
    # Keep a "final" copy for the runtime service.
    shutil.copy2(artifact.best_weights, ANN_FINAL_PATH)
    return artifact


def train_rnn_model(
    splits: dict[str, pd.DataFrame],
    config: TrainConfig,
    device: torch.device,
) -> TrainingArtifact:
    train_inputs, train_condition, train_health, train_life = _build_sequence_tensors(splits["train"])
    val_inputs, val_condition, val_health, val_life = _build_sequence_tensors(splits["validation"])
    test_inputs, test_condition, test_health, test_life = _build_sequence_tensors(splits["test"])

    train_loader = _build_loader(train_inputs, train_condition, train_health, train_life, config.rnn_batch_size, True)
    val_loader = _build_loader(val_inputs, val_condition, val_health, val_life, config.rnn_batch_size, False)
    test_loader = _build_loader(test_inputs, test_condition, test_health, test_life, config.rnn_batch_size, False)

    model = SequenceConditionModel(input_dim=train_inputs.shape[-1])
    return _train_model(
        name="rnn",
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        device=device,
        epochs=config.rnn_epochs,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        patience=config.patience,
        artifact_dir=MODEL_DIR / "rnn",
    )


def train_cnn_model(
    splits: dict[str, pd.DataFrame],
    config: TrainConfig,
    device: torch.device,
) -> TrainingArtifact:
    train_inputs, train_condition, train_health, train_life, train_skipped = _build_image_tensors(
        splits["train"],
        config.cnn_image_size,
        augment_copies=config.cnn_augment_copies,
        include_edge_channel=config.cnn_include_edge_channel,
        center_crop_ratio=config.cnn_center_crop_ratio,
        raw_rgb=config.cnn_raw_rgb,
    )
    val_inputs, val_condition, val_health, val_life, val_skipped = _build_image_tensors(
        splits["validation"],
        config.cnn_image_size,
        include_edge_channel=config.cnn_include_edge_channel,
        center_crop_ratio=config.cnn_center_crop_ratio,
        raw_rgb=config.cnn_raw_rgb,
    )
    test_inputs, test_condition, test_health, test_life, test_skipped = _build_image_tensors(
        splits["test"],
        config.cnn_image_size,
        include_edge_channel=config.cnn_include_edge_channel,
        center_crop_ratio=config.cnn_center_crop_ratio,
        raw_rgb=config.cnn_raw_rgb,
    )

    logger.info(
        "CNN usable tensors - train=%d val=%d test=%d (skipped source rows: %d/%d/%d)",
        len(train_inputs),
        len(val_inputs),
        len(test_inputs),
        train_skipped,
        val_skipped,
        test_skipped,
    )
    logger.info(
        "CNN architecture: %s (pretrained=%s, freeze_encoder=%s, raw_rgb=%s, augment_copies=%d, balanced_sampler=%s, edge_channel=%s, center_crop_ratio=%.2f)",
        config.cnn_architecture,
        config.cnn_pretrained,
        config.cnn_freeze_encoder,
        config.cnn_raw_rgb,
        config.cnn_augment_copies,
        config.cnn_balanced_sampler,
        config.cnn_include_edge_channel,
        config.cnn_center_crop_ratio,
    )

    if config.cnn_balanced_sampler:
        train_loader = _build_balanced_loader(
            train_inputs,
            train_condition,
            train_health,
            train_life,
            config.cnn_batch_size,
        )
    else:
        train_loader = _build_loader(train_inputs, train_condition, train_health, train_life, config.cnn_batch_size, True)
    val_loader = _build_loader(val_inputs, val_condition, val_health, val_life, config.cnn_batch_size, False)
    test_loader = _build_loader(test_inputs, test_condition, test_health, test_life, config.cnn_batch_size, False)

    model = build_image_model(config, in_channels=train_inputs.shape[1])
    return _train_model(
        name="cnn",
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        device=device,
        epochs=config.cnn_epochs,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        patience=config.patience,
        artifact_dir=MODEL_DIR / "cnn",
        condition_loss_weight=config.cnn_condition_loss_weight,
        health_loss_weight=config.cnn_regression_loss_weight,
        life_loss_weight=config.cnn_regression_loss_weight,
        monitor_metric="condition_accuracy",
        monitor_mode="max",
    )


def write_metadata(
    full_df: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
    ann_artifact: TrainingArtifact,
    runtime_device: torch.device,
) -> None:
    metadata = {
        "features": FEATURE_COLUMNS,
        "feature_max": FEATURE_MAX.tolist(),
        "condition_classes": CONDITION_LABELS,
        "health_max": MAX_HEALTH_SCORE,
        "remaining_life_max_km": SAFE_TIRE_LIFE_KM,
        "model_type": "SmartTireTabular",
        "total_rows": int(len(full_df)),
        "rows_with_images": int(full_df["has_image"].sum()),
        "train_rows": int(len(splits["train"])),
        "validation_rows": int(len(splits["validation"])),
        "test_rows": int(len(splits["test"])),
        "device_used_for_training": runtime_device.type,
        "best_val_loss": ann_artifact.val_metrics["loss"],
        "best_val_accuracy": ann_artifact.val_metrics["condition_accuracy"],
        "test_accuracy": ann_artifact.test_metrics["condition_accuracy"],
        "test_health_mae": ann_artifact.test_metrics["health_mae"],
        "test_remaining_life_mae_km": ann_artifact.test_metrics["remaining_life_mae_km"],
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def write_registry(
    full_df: pd.DataFrame,
    artifacts: list[TrainingArtifact],
    config: TrainConfig,
) -> None:
    registry = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "dataset": {
            "rows": int(len(full_df)),
            "rows_with_images": int(full_df["has_image"].sum()),
            "condition_distribution": full_df["condition"].value_counts().to_dict(),
            "wear_distribution": full_df["wear_pattern"].value_counts().to_dict(),
        },
        "runtime_model": "ann",
        "training_config": {
            "ann_epochs": config.ann_epochs,
            "rnn_epochs": config.rnn_epochs,
            "cnn_epochs": config.cnn_epochs,
            "learning_rate": config.learning_rate,
            "weight_decay": config.weight_decay,
            "patience": config.patience,
            "cnn_image_size": config.cnn_image_size,
            "cnn_architecture": config.cnn_architecture,
            "cnn_pretrained": config.cnn_pretrained,
            "cnn_augment_copies": config.cnn_augment_copies,
            "cnn_balanced_sampler": config.cnn_balanced_sampler,
            "cnn_condition_loss_weight": config.cnn_condition_loss_weight,
            "cnn_regression_loss_weight": config.cnn_regression_loss_weight,
            "cnn_include_edge_channel": config.cnn_include_edge_channel,
            "cnn_center_crop_ratio": config.cnn_center_crop_ratio,
            "cnn_freeze_encoder": config.cnn_freeze_encoder,
            "cnn_raw_rgb": config.cnn_raw_rgb,
            "max_samples": config.max_samples,
        },
        "models": {
            artifact.name: {
                "best_weights": str(artifact.best_weights.relative_to(ROOT)),
                "history": str(artifact.history_path.relative_to(ROOT)),
                "validation_metrics": artifact.val_metrics,
                "test_metrics": artifact.test_metrics,
            }
            for artifact in artifacts
        },
    }
    REGISTRY_JSON.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def parse_args() -> TrainConfig | argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess dataset and train Smart Tire models")
    parser.add_argument(
        "--fresh-hybrid",
        action="store_true",
        help="Use the fresh PyTorch EfficientNetV2-B0 + ViT-B/16 + BiLSTM + fusion training pipeline.",
    )
    parser.add_argument(
        "--archive-old",
        action="store_true",
        help="Archive existing ai_model/saved_models artifacts before fresh hybrid training.",
    )
    parser.add_argument(
        "--full-train",
        action="store_true",
        help="Require pretrained EfficientNetV2-B0/ViT-B/16 weights and train on the full prepared split data.",
    )
    parser.add_argument("--hybrid-stage1-epochs", type=int, default=8)
    parser.add_argument("--hybrid-stage2-epochs", type=int, default=12)
    parser.add_argument("--hybrid-batch-size", type=int, default=2)
    parser.add_argument("--hybrid-stage2-batch-size", type=int, default=1)
    parser.add_argument("--hybrid-grad-accum-steps", type=int, default=8)
    parser.add_argument("--hybrid-learning-rate", type=float, default=1e-4)
    parser.add_argument("--hybrid-fine-tune-learning-rate", type=float, default=1e-5)
    parser.add_argument(
        "--hybrid-sequence-source",
        choices=["runtime_visual_proxy", "constant", "labels"],
        default="runtime_visual_proxy",
        help=(
            "Tread sequence input for PyTorch hybrid training. "
            "Use runtime_visual_proxy for deployable metrics; labels is oracle-only."
        ),
    )
    parser.add_argument(
        "--hybrid-resume-checkpoint",
        default=None,
        help="Optional existing hybrid checkpoint to resume/fine-tune from.",
    )
    parser.add_argument(
        "--hybrid-pretrained",
        action="store_true",
        help="Load pretrained EfficientNetV2-B0/ViT-B/16 weights for a non-full training run.",
    )
    parser.add_argument("--ann-epochs", type=int, default=18)
    parser.add_argument("--rnn-epochs", type=int, default=18)
    parser.add_argument("--cnn-epochs", type=int, default=8)
    parser.add_argument("--ann-batch-size", type=int, default=64)
    parser.add_argument("--rnn-batch-size", type=int, default=64)
    parser.add_argument("--cnn-batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--cnn-image-size", type=int, default=128)
    parser.add_argument(
        "--cnn-architecture",
        choices=["compact", "densenet121", "resnet18"],
        default="compact",
        help="CNN backbone to train. Use densenet121 for transfer-learning experiments.",
    )
    parser.add_argument(
        "--cnn-pretrained",
        action="store_true",
        help="Load ImageNet pretrained weights for supported CNN backbones.",
    )
    parser.add_argument(
        "--cnn-augment-copies",
        type=int,
        default=0,
        help="Extra augmented copies per training image for CNN training only.",
    )
    parser.add_argument(
        "--cnn-balanced-sampler",
        action="store_true",
        help="Sample CNN training batches with class balancing.",
    )
    parser.add_argument(
        "--cnn-condition-loss-weight",
        type=float,
        default=1.0,
        help="Condition-classification loss weight for CNN training.",
    )
    parser.add_argument(
        "--cnn-regression-loss-weight",
        type=float,
        default=0.5,
        help="Health/life regression loss weight for CNN training.",
    )
    parser.add_argument(
        "--cnn-no-edge-channel",
        action="store_true",
        help="Train CNN on 3-channel RGB tensors instead of RGB plus edge channel.",
    )
    parser.add_argument(
        "--cnn-center-crop-ratio",
        type=float,
        default=1.0,
        help="Optional centered crop ratio before CNN preprocessing, e.g. 0.75.",
    )
    parser.add_argument(
        "--cnn-freeze-encoder",
        action="store_true",
        help="Freeze pretrained CNN encoder and train only task heads.",
    )
    parser.add_argument(
        "--cnn-raw-rgb",
        action="store_true",
        help="Use raw resized RGB inputs with ImageNet normalization for pretrained CNNs.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optional stratified row limit for quick smoke training. Omit for full dataset training.",
    )
    parser.add_argument(
        "--reuse-prepared",
        action="store_true",
        help="Reuse dataset/processed/features.csv instead of rebuilding dataset artifacts first.",
    )
    args = parser.parse_args()
    if args.fresh_hybrid:
        return args

    return TrainConfig(
        ann_epochs=args.ann_epochs,
        rnn_epochs=args.rnn_epochs,
        cnn_epochs=args.cnn_epochs,
        ann_batch_size=args.ann_batch_size,
        rnn_batch_size=args.rnn_batch_size,
        cnn_batch_size=args.cnn_batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        patience=args.patience,
        cnn_image_size=args.cnn_image_size,
        cnn_architecture=args.cnn_architecture,
        cnn_pretrained=args.cnn_pretrained,
        cnn_augment_copies=max(0, args.cnn_augment_copies),
        cnn_balanced_sampler=args.cnn_balanced_sampler,
        cnn_condition_loss_weight=max(0.0, args.cnn_condition_loss_weight),
        cnn_regression_loss_weight=max(0.0, args.cnn_regression_loss_weight),
        cnn_include_edge_channel=not args.cnn_no_edge_channel,
        cnn_center_crop_ratio=float(np.clip(args.cnn_center_crop_ratio, 0.2, 1.0)),
        cnn_freeze_encoder=args.cnn_freeze_encoder,
        cnn_raw_rgb=args.cnn_raw_rgb,
        max_samples=args.max_samples,
        reuse_prepared=args.reuse_prepared,
    )


def print_summary(artifacts: list[TrainingArtifact]) -> None:
    print("")
    print("=" * 76)
    print("SMART TIRE ANALYZER TRAINING SUMMARY")
    print("=" * 76)
    for artifact in artifacts:
        print(
            f"{artifact.name.upper():<4} | "
            f"val_acc={artifact.val_metrics['condition_accuracy']:.3f} | "
            f"test_acc={artifact.test_metrics['condition_accuracy']:.3f} | "
            f"test_health_mae={artifact.test_metrics['health_mae']:.3f} | "
            f"test_life_mae={artifact.test_metrics['remaining_life_mae_km']:.2f}km"
        )
    print("=" * 76)
    print(f"Runtime ANN weights refreshed at: {ANN_BEST_PATH}")
    print("")


def main() -> None:
    _ensure_runtime_dirs()
    set_seed(SEED)
    config = parse_args()
    if getattr(config, "fresh_hybrid", False):
        from ai_model.hybrid_torch.trainer import train_from_cli_args

        train_from_cli_args(config, ROOT)
        return

    device = choose_device()

    logger.info("Using device: %s", device)
    enriched_df = prepare_features_for_training(reuse_prepared=config.reuse_prepared)
    enriched_df = limit_training_rows(enriched_df, config.max_samples)
    splits = split_dataset(enriched_df)

    ann_artifact = train_ann_model(splits, config, device)
    rnn_artifact = train_rnn_model(splits, config, device)
    cnn_artifact = train_cnn_model(splits, config, device)

    artifacts = [ann_artifact, rnn_artifact, cnn_artifact]
    write_metadata(enriched_df, splits, ann_artifact, device)
    write_registry(enriched_df, artifacts, config)
    print_summary(artifacts)


if __name__ == "__main__":
    main()
