"""Dataset and preprocessing utilities for the PyTorch hybrid model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import Dataset

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

from ai_model.hybrid_torch.constants import (
    CONDITION_LABELS,
    HEALTH_MAX,
    IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MAX_REMAINING_KM,
    TREAD_MAX_MM,
    WEAR_ALIASES,
    WEAR_LABELS,
)
from ai_model.hybrid_torch.runtime_tread import (
    RUNTIME_TREAD_SEQUENCE_SOURCE,
    estimate_visual_tread_depths,
)
from ai_model.rnn.sequence_builder import build_tread_sequence

TREAD_COLUMNS = ("tread_1", "tread_2", "tread_3", "tread_4")
IMAGE_PATH_COLUMNS = ("image_path", "front_image_path", "dataset_front_path")


def canonical_wear_label(value: object) -> str:
    """Map historical labels into the six runtime wear classes."""
    key = str(value or "uniform_wear").strip().lower()
    return WEAR_ALIASES.get(key, "patchy_wear")


def wear_label_to_id(value: object) -> int:
    label = canonical_wear_label(value)
    return WEAR_LABELS.index(label)


def resolve_image_path(row: pd.Series) -> Path | None:
    """Resolve the best existing tread image path from a prepared split row."""
    for column in IMAGE_PATH_COLUMNS:
        value = row.get(column)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        path_text = str(value).strip()
        if not path_text or path_text.lower() == "nan":
            continue
        path = Path(path_text)
        if path.is_file():
            return path
    return None


def is_readable_image(path: Path) -> bool:
    try:
        with Image.open(str(path)) as image:
            image.verify()
        return True
    except Exception:
        return False


def _center_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def pil_to_imagenet_tensor(image: Image.Image, image_size: int = IMAGE_SIZE) -> torch.Tensor:
    """Convert a PIL RGB image to an ImageNet-normalized CHW tensor."""
    image = _center_square(image.convert("RGB"))
    image = image.resize((image_size, image_size), Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.asarray(IMAGENET_MEAN, dtype=np.float32)) / np.asarray(
        IMAGENET_STD,
        dtype=np.float32,
    )
    array = np.transpose(array, (2, 0, 1)).astype(np.float32, copy=False)
    return torch.from_numpy(array)


def bgr_image_to_tensor(image_bgr: np.ndarray, image_size: int = IMAGE_SIZE) -> torch.Tensor:
    """Convert an OpenCV BGR image to an ImageNet-normalized CHW tensor."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return pil_to_imagenet_tensor(Image.fromarray(rgb), image_size=image_size)


def load_split_frame(split_dir: Path) -> pd.DataFrame:
    labels_path = split_dir / "labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(f"Missing split labels: {labels_path}")
    frame = pd.read_csv(labels_path)
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        image_path = resolve_image_path(row)
        if image_path is None:
            continue
        if not is_readable_image(image_path):
            continue
        record = row.to_dict()
        record["resolved_image_path"] = str(image_path)
        rows.append(record)
    if not rows:
        raise RuntimeError(f"No usable image rows found in {labels_path}")
    return pd.DataFrame(rows).reset_index(drop=True)


class HybridTireDataset(Dataset):
    """Prepared tire split dataset for image + tread-sequence multitask training."""

    def __init__(
        self,
        split_dir: str | Path,
        image_size: int = IMAGE_SIZE,
        sequence_source: str = RUNTIME_TREAD_SEQUENCE_SOURCE,
    ) -> None:
        self.split_dir = Path(split_dir)
        self.image_size = int(image_size)
        self.sequence_source = str(sequence_source)
        self.frame = load_split_frame(self.split_dir)
        self._sequence_cache: dict[str, np.ndarray] = {}

    def __len__(self) -> int:
        return int(len(self.frame))

    def __getitem__(self, index: int) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        row = self.frame.iloc[index]
        image_path = str(row["resolved_image_path"])
        image = Image.open(image_path)
        image_tensor = pil_to_imagenet_tensor(image, image_size=self.image_size)

        tread_mm = np.asarray([float(row[column]) for column in TREAD_COLUMNS], dtype=np.float32)
        tread_mm = np.nan_to_num(tread_mm, nan=float(np.nanmean(tread_mm)))
        tread_mm = np.clip(tread_mm, 0.0, TREAD_MAX_MM).astype(np.float32)
        sequence_depths = self._sequence_depths(image_path, image, tread_mm)
        tread_sequence = torch.from_numpy(build_tread_sequence(sequence_depths.tolist()).astype(np.float32))

        health_norm = float(row.get("health_norm", float(np.mean(tread_mm) / TREAD_MAX_MM)))
        life_norm = float(row.get("remaining_life_norm", 0.5))
        condition_id = int(row.get("condition_id", 0))
        condition_id = max(0, min(condition_id, len(CONDITION_LABELS) - 1))

        inputs = {
            "image": image_tensor,
            "tread_sequence": tread_sequence,
        }
        targets = {
            "tread_depths": torch.tensor(tread_mm / TREAD_MAX_MM, dtype=torch.float32),
            "health_score": torch.tensor([np.clip(health_norm, 0.0, 1.0)], dtype=torch.float32),
            "remaining_life": torch.tensor([np.clip(life_norm, 0.0, 1.0)], dtype=torch.float32),
            "wear_pattern": torch.tensor(wear_label_to_id(row.get("wear_pattern")), dtype=torch.long),
            "condition": torch.tensor(condition_id, dtype=torch.long),
        }
        return inputs, targets

    def _sequence_depths(self, image_path: str, image: Image.Image, tread_mm: np.ndarray) -> np.ndarray:
        source = self.sequence_source.strip().lower()
        if source in {"label", "labels", "oracle", "ground_truth"}:
            return tread_mm.astype(np.float32, copy=False)
        if source in {"constant", "neutral"}:
            return np.full(4, 4.2, dtype=np.float32)

        cached = self._sequence_cache.get(image_path)
        if cached is not None:
            return cached

        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        image_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        estimated = np.asarray(estimate_visual_tread_depths(image_bgr), dtype=np.float32)
        self._sequence_cache[image_path] = estimated
        return estimated


def split_summary(split_root: str | Path = "dataset/splits") -> dict[str, int]:
    root = Path(split_root)
    return {
        split: len(load_split_frame(root / split))
        for split in ("train", "validation", "test")
        if (root / split / "labels.csv").exists()
    }
