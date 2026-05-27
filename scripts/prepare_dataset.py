"""
One-command raw dataset preparation for Smart Tire Analyzer.

Run from the project root after updating raw files:
    python scripts/prepare_dataset.py

The script rebuilds generated dataset artifacts from either layout:
    dataset/raw/labels.csv
    dataset/raw/images/front_view/
    dataset/raw/images/sidewall/
    dataset/raw/learning_samples/labels.csv
    dataset/raw/learning_samples/front_view/
    dataset/raw/learning_samples/sidewall/

or the legacy project layout:
    dataset/raw/spreadsheet/*.xlsx
    dataset/raw/tread_images/
    dataset/raw/sidewall_images/

It also folds in corrected samples saved by the app under:
    dataset/continuous_learning/labels.csv
    dataset/continuous_learning/front_view/

Raw inputs are never modified.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET_DIR = ROOT / "dataset"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif"}
SEED = 42
SAFE_TIRE_LIFE_KM = 80_000.0
MAX_TREAD_MM = 12.0
NEW_TIRE_DEPTH_MM = 8.0
LEGAL_MIN_TREAD_MM = 1.6


def _load_train_test_split():
    """Import sklearn splitting lazily to avoid Windows torch DLL load conflicts."""
    try:
        from sklearn.model_selection import train_test_split
    except Exception:  # pragma: no cover - fallback is exercised only without sklearn installed.
        return None
    return train_test_split

CONDITION_TO_ID = {"safe": 0, "moderate": 1, "replace": 2}
WEAR_TO_ID = {
    "center_wear": 0,
    "edge_wear": 1,
    "uneven_wear": 2,
    "even": 3,
    "one_sided_wear": 4,
    "critical_wear": 5,
}

BRAND_MAP = {
    "apollo": "Apollo",
    "applo": "Apollo",
    "bf goodrich": "BF Goodrich",
    "bridgeston": "Bridgestone",
    "bridgestone": "Bridgestone",
    "bridgstone": "Bridgestone",
    "ceat": "CEAT",
    "continental": "Continental",
    "continetal": "Continental",
    "dunlop": "Dunlop",
    "dunlop tires": "Dunlop",
    "firestone": "Firestone",
    "good year": "Goodyear",
    "goodyear": "Goodyear",
    "goodyer": "Goodyear",
    "jk tyre": "JK Tyre",
    "jktyre": "JK Tyre",
    "kelly": "Kelly",
    "maxtrek": "Maxtrek",
    "michelin": "Michelin",
    "michelino": "Michelin",
    "michilen": "Michelin",
    "mrf": "MRF",
    "pireli": "Pirelli",
    "pirelli": "Pirelli",
    "pirelly": "Pirelli",
    "toyo": "Toyo",
    "yokohama": "Yokohama",
    "yokohamma": "Yokohama",
}

RENAME_MAP = {
    "Front Profile": "image_id",
    "Side Profile URL": "sidewall_image_id",
    "Tread 1": "tread_1",
    "Tread 2": "tread_2",
    "Tread 3": "tread_3",
    "Tread 4": "tread_4",
    "Average form": "tread_average",
    "Company name": "brand",
    "model": "tire_model",
    "Tire Size": "tire_size",
    "DOT & DOM": "ocr_text",
    "Company Manufacture": "manufacture_country",
    "TUBE/TUBELESS": "tube_type",
}

COLUMN_ALIASES = {
    "image_id": {
        "image_id",
        "image",
        "image_name",
        "image_filename",
        "filename",
        "file_name",
        "front_image_id",
        "front_image_name",
        "front_view",
        "front_view_image",
        "front_profile",
        "front profile",
    },
    "front_image_reference": {
        "front_image",
        "front_image_path",
        "image_path",
        "front_path",
        "front_filename",
        "front_view_path",
    },
    "sidewall_image_id": {
        "sidewall_image_id",
        "sidewall",
        "sidewall_image",
        "sidewall_image_name",
        "sidewall_image_path",
        "sidewall_path",
        "sidewall_view",
        "side_profile_url",
        "side profile url",
    },
    "tread_1": {"tread_1", "tread1", "t1", "tread 1"},
    "tread_2": {"tread_2", "tread2", "t2", "tread 2"},
    "tread_3": {"tread_3", "tread3", "t3", "tread 3"},
    "tread_4": {"tread_4", "tread4", "t4", "tread 4"},
    "tread_average": {
        "tread_average",
        "average_tread",
        "avg_tread",
        "average form",
        "average_form",
    },
    "brand": {"brand", "company", "company_name", "company name", "manufacturer"},
    "tire_model": {"tire_model", "model", "tyre_model"},
    "tire_size": {"tire_size", "tire size", "tyre_size", "size"},
    "li_si": {"li_si", "li & si", "li_si_rating"},
    "ocr_text": {"ocr_text", "dot", "dot_dom", "dot & dom", "dot_and_dom"},
    "tube_type": {"tube_type", "tube", "tube/tubeless", "tube_tubeless"},
}

BASE_LABEL_COLUMNS = [
    "image_id",
    "front_image_reference",
    "sidewall_image_id",
    "tread_1",
    "tread_2",
    "tread_3",
    "tread_4",
    "tread_average",
    "brand",
    "tire_model",
    "tire_size",
    "li_si",
    "ocr_text",
    "tube_type",
]

FEATURE_COLUMNS = [
    "image_id",
    "sidewall_image_id",
    "tread_1",
    "tread_2",
    "tread_3",
    "tread_4",
    "tread_average",
    "brand",
    "tire_model",
    "tire_size",
    "condition",
    "condition_id",
    "wear_pattern",
    "wear_class_6",
    "health_score",
    "health_norm",
    "remaining_life_km",
    "remaining_life_norm",
    "remaining_life_pred",
    "replacement_urgency",
    "risk_score",
    "risk_level",
    "replace_recommended",
    "manufacture_week",
    "manufacture_year",
    "ocr_confidence",
    "tube_type",
    "image_path",
    "front_image_path",
    "sidewall_image_path",
    "dataset_front_path",
    "dataset_sidewall_path",
    "has_image",
    "has_sidewall_image",
    "feature_tread_spread",
    "feature_center_edge_gap",
]


@dataclass(frozen=True)
class DatasetPaths:
    root: Path = DATASET_DIR

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def raw_labels_csv(self) -> Path:
        return self.raw_dir / "labels.csv"

    @property
    def raw_images_dir(self) -> Path:
        return self.raw_dir / "images"

    @property
    def raw_front_images_dir(self) -> Path:
        return self.raw_images_dir / "front_view"

    @property
    def raw_sidewall_images_dir(self) -> Path:
        return self.raw_images_dir / "sidewall"

    @property
    def learning_samples_dir(self) -> Path:
        return self.raw_dir / "learning_samples"

    @property
    def learning_labels_csv(self) -> Path:
        return self.learning_samples_dir / "labels.csv"

    @property
    def learning_front_images_dir(self) -> Path:
        return self.learning_samples_dir / "front_view"

    @property
    def learning_sidewall_images_dir(self) -> Path:
        return self.learning_samples_dir / "sidewall"

    @property
    def continuous_learning_dir(self) -> Path:
        return self.root / "continuous_learning"

    @property
    def continuous_learning_labels_csv(self) -> Path:
        return self.continuous_learning_dir / "labels.csv"

    @property
    def continuous_front_images_dir(self) -> Path:
        return self.continuous_learning_dir / "front_view"

    @property
    def spreadsheet_dir(self) -> Path:
        return self.raw_dir / "spreadsheet"

    @property
    def tread_images_dir(self) -> Path:
        return self.raw_dir / "tread_images"

    @property
    def sidewall_images_dir(self) -> Path:
        return self.raw_dir / "sidewall_images"

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed"

    @property
    def labels_dir(self) -> Path:
        return self.root / "labels"

    @property
    def annotations_dir(self) -> Path:
        return self.root / "annotations"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def metadata_dir(self) -> Path:
        return self.root / "metadata"

    @property
    def multi_view_dir(self) -> Path:
        return self.root / "multi_view"

    @property
    def splits_dir(self) -> Path:
        return self.root / "splits"

    @property
    def labels_csv(self) -> Path:
        return self.processed_dir / "labels.csv"

    @property
    def cleaned_csv(self) -> Path:
        return self.processed_dir / "cleaned_dataset.csv"

    @property
    def features_csv(self) -> Path:
        return self.processed_dir / "features.csv"

    @property
    def manifest_json(self) -> Path:
        return self.metadata_dir / "dataset_manifest.json"


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("prepare_dataset")


def normalize_image_key(value: object) -> str:
    """Return a lenient filename key that ignores extension, punctuation, and case."""
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\.(jpg|jpeg|png|bmp|webp|heic|heif)$", "", text, flags=re.IGNORECASE)
    text = text.replace("copy of ", "")
    text = re.sub(r"\[\d+\]", "", text)
    text = text.replace("(1)", "").replace("(2)", "")
    return re.sub(r"[^a-z0-9]", "", text)


def clean_brand(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    text = re.sub(r"[^a-zA-Z0-9 &]", " ", str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return "Unknown"
    return BRAND_MAP.get(text.lower(), text.title())


def clean_tire_size(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    text = str(value).upper().strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("-", "").replace("\\", "/")
    match = re.match(r"(\d{3})/?(\d{2})R?(\d{2})", text)
    if match:
        return f"{match.group(1)}/{match.group(2)} R{match.group(3)}"
    return str(value).strip() or "Unknown"


def extract_dot_date(value: object) -> tuple[float, float]:
    if pd.isna(value):
        return np.nan, np.nan
    matches = re.findall(r"(\d{2})(\d{2})", str(value))
    for week_text, year_text in reversed(matches):
        week = int(week_text)
        if 1 <= week <= 53:
            year = int(year_text)
            full_year = 2000 + year if year <= 79 else 1900 + year
            return float(week), float(full_year)
    return np.nan, np.nan


def tread_to_condition(avg_tread_mm: float) -> str:
    if avg_tread_mm >= 4.0:
        return "safe"
    if avg_tread_mm >= LEGAL_MIN_TREAD_MM:
        return "moderate"
    return "replace"


def tread_depth_class(avg_tread_mm: float) -> str:
    if avg_tread_mm >= 8.0:
        return "New"
    if avg_tread_mm >= 6.0:
        return "Good"
    if avg_tread_mm >= 4.0:
        return "Moderate"
    if avg_tread_mm >= 2.0:
        return "Replace Soon"
    return "Dangerous"


def tread_to_wear(row: pd.Series) -> str:
    values = [float(row[column]) for column in ("tread_1", "tread_2", "tread_3", "tread_4")]
    tread_range = max(values) - min(values)
    center = float(np.mean([values[1], values[2]]))
    edges = float(np.mean([values[0], values[3]]))

    if float(row["tread_average"]) < LEGAL_MIN_TREAD_MM:
        return "critical_wear"
    if tread_range < 0.5:
        return "even"
    if center > edges + 0.5:
        return "center_wear"
    if edges > center + 0.5:
        return "edge_wear"
    if abs(values[0] - values[3]) > 1.0:
        return "one_sided_wear"
    if tread_range > 2.0:
        return "critical_wear"
    return "uneven_wear"


def wear_severity(wear_pattern: str, condition: str) -> str:
    if condition == "replace" or wear_pattern == "critical_wear":
        return "high"
    if condition == "moderate" or wear_pattern in {"edge_wear", "one_sided_wear", "uneven_wear"}:
        return "moderate"
    return "low"


def replacement_urgency(remaining_life_pct: float) -> str:
    if pd.isna(remaining_life_pct):
        return "Unknown"
    if remaining_life_pct > 70:
        return "Low"
    if remaining_life_pct >= 40:
        return "Medium"
    if remaining_life_pct >= 20:
        return "High"
    return "Immediate"


def compute_risk_score(row: pd.Series) -> int:
    score = 0
    tread_avg = float(row["tread_average"])
    if tread_avg < 3.0:
        score += 30
    if tread_avg < LEGAL_MIN_TREAD_MM:
        score += 25
    if row["wear_pattern"] in {"edge_wear", "one_sided_wear", "uneven_wear"}:
        score += 20
    if row["wear_pattern"] == "critical_wear":
        score += 30
    if not pd.isna(row.get("manufacture_year")):
        age = datetime.now().year - int(row["manufacture_year"])
        if age > 5:
            score += 20
    return int(min(score, 100))


def risk_label(score: int) -> str:
    if score <= 25:
        return "LOW"
    if score <= 50:
        return "MODERATE"
    if score <= 75:
        return "HIGH"
    return "CRITICAL"


def newest_spreadsheet(spreadsheet_dir: Path) -> Path:
    """Return the newest supported label file from the spreadsheet folder."""
    files = sorted(
        (
            path
            for path in spreadsheet_dir.iterdir()
            if path.is_file()
            and not path.name.startswith("~$")
            and path.suffix.lower() in {".csv", ".xlsx", ".xls"}
        ),
        key=lambda path: (path.stat().st_mtime, path.name.lower()),
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No .csv, .xlsx, or .xls labels found in {spreadsheet_dir}")
    return files[0]


def normalize_column_name(value: object) -> str:
    """Normalize user-provided CSV/XLSX headers for alias matching."""
    text = str(value).strip().lower()
    text = text.replace("-", "_").replace("/", "_")
    text = re.sub(r"\s+", "_", text)
    return re.sub(r"[^a-z0-9_&]", "", text)


def normalize_spreadsheet_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {
        old: new for old, new in RENAME_MAP.items() if old in raw_df.columns
    }
    claimed_targets = set(rename.values())
    for column in raw_df.columns:
        if column in rename:
            continue
        normalized = normalize_column_name(column)
        loose = normalized.replace("_", " ")
        for target, aliases in COLUMN_ALIASES.items():
            normalized_aliases = {normalize_column_name(alias) for alias in aliases}
            loose_aliases = {normalize_column_name(alias).replace("_", " ") for alias in aliases}
            if target not in claimed_targets and (
                normalized in normalized_aliases or loose in loose_aliases
            ):
                rename[column] = target
                claimed_targets.add(target)
                break

    df = raw_df.rename(columns=rename).copy()
    if "LI & SI" in df.columns:
        df = df.rename(columns={"LI & SI": "li_si"})
    for column in BASE_LABEL_COLUMNS:
        if column not in df.columns:
            df[column] = np.nan
    df["image_id"] = df["image_id"].astype("object")
    df["front_image_reference"] = df["front_image_reference"].astype("object")
    image_missing = df["image_id"].isna() | (df["image_id"].astype(str).str.strip() == "")
    df.loc[image_missing, "image_id"] = df.loc[image_missing, "front_image_reference"]
    return df[BASE_LABEL_COLUMNS].copy()


def has_tread_label(row: pd.Series) -> bool:
    """Return True when a learning row has enough tread data to train on."""
    for column in ("tread_1", "tread_2", "tread_3", "tread_4", "tread_average"):
        value = row.get(column)
        if pd.notna(value) and str(value).strip() != "":
            return True
    return False


def load_learning_label_frames(paths: DatasetPaths) -> list[pd.DataFrame]:
    """Load optional manually-added and app-corrected learning samples."""
    frames: list[pd.DataFrame] = []
    for labels_path in (paths.learning_labels_csv, paths.continuous_learning_labels_csv):
        if not labels_path.exists():
            continue
        raw_frame = read_source_labels(labels_path)
        normalized = normalize_spreadsheet_columns(raw_frame)
        normalized = normalized[normalized.apply(has_tread_label, axis=1)].copy()
        if normalized.empty:
            logger.warning("No trainable tread labels found in %s", labels_path)
            continue
        logger.info("Loaded %d learning samples from %s", len(normalized), labels_path)
        frames.append(normalized)
    return frames


def repair_tread_depths(df: pd.DataFrame) -> pd.DataFrame:
    repaired = df.copy()
    tread_cols = ["tread_1", "tread_2", "tread_3", "tread_4"]
    for column in tread_cols:
        repaired[column] = pd.to_numeric(repaired[column], errors="coerce")

    for column in tread_cols:
        missing = repaired[column].isna() | (repaired[column] == 0.0)
        if missing.any():
            peers = [peer for peer in tread_cols if peer != column]
            repaired.loc[missing, column] = repaired.loc[missing, peers].replace(0.0, np.nan).mean(axis=1)

    for column in tread_cols:
        repaired[column] = repaired[column].fillna(repaired[tread_cols].mean(axis=1))
        repaired[column] = repaired[column].fillna(0.0).clip(0.0, MAX_TREAD_MM)

    repaired["tread_average"] = repaired[tread_cols].mean(axis=1)
    return repaired


def clean_and_enrich(base_df: pd.DataFrame) -> pd.DataFrame:
    cleaned = base_df.dropna(subset=["image_id"]).copy()
    cleaned["image_id"] = cleaned["image_id"].astype(str).str.strip()
    cleaned = cleaned[cleaned["image_id"] != ""].drop_duplicates(subset=["image_id"]).reset_index(drop=True)
    cleaned = repair_tread_depths(cleaned)

    cleaned["brand"] = cleaned["brand"].apply(clean_brand)
    cleaned["tire_model"] = cleaned["tire_model"].fillna("").astype(str).str.strip()
    cleaned["tire_size"] = cleaned["tire_size"].apply(clean_tire_size)
    cleaned["front_image_reference"] = cleaned["front_image_reference"].fillna("").astype(str).str.strip()
    cleaned["sidewall_image_id"] = cleaned["sidewall_image_id"].fillna("").astype(str).str.strip()
    cleaned["ocr_text"] = cleaned["ocr_text"].fillna("").astype(str).str.strip()
    cleaned["tube_type"] = cleaned["tube_type"].fillna("").astype(str).str.strip()

    dot_dates = cleaned["ocr_text"].apply(extract_dot_date)
    cleaned["manufacture_week"] = [date[0] for date in dot_dates]
    cleaned["manufacture_year"] = [date[1] for date in dot_dates]
    cleaned["ocr_confidence"] = np.where(cleaned["ocr_text"].str.len() > 0, 0.95, 0.30)

    cleaned["condition"] = cleaned["tread_average"].apply(tread_to_condition)
    cleaned["condition_id"] = cleaned["condition"].map(CONDITION_TO_ID).astype(int)
    cleaned["wear_pattern"] = cleaned.apply(tread_to_wear, axis=1)
    cleaned["wear_class_6"] = cleaned["wear_pattern"].map(WEAR_TO_ID).fillna(2).astype(int)

    cleaned["tread_percent"] = ((cleaned["tread_average"] / NEW_TIRE_DEPTH_MM) * 100.0).clip(0.0, 100.0)
    shape_scores = {"safe": 90.0, "moderate": 55.0, "replace": 20.0}
    surface_scores = cleaned["wear_pattern"].map(
        {
            "even": 100.0,
            "center_wear": 80.0,
            "edge_wear": 65.0,
            "one_sided_wear": 55.0,
            "uneven_wear": 60.0,
            "critical_wear": 20.0,
        }
    ).fillna(60.0)
    cleaned["health_score"] = (
        ((0.5 * cleaned["tread_percent"]) + (0.3 * cleaned["condition"].map(shape_scores)) + (0.2 * surface_scores))
        / 10.0
    ).clip(0.0, 10.0).round(2)

    cleaned["remaining_life_pred"] = (
        ((cleaned["tread_average"] - LEGAL_MIN_TREAD_MM) / (NEW_TIRE_DEPTH_MM - LEGAL_MIN_TREAD_MM)) * 100.0
    ).clip(0.0, 100.0)
    cleaned["remaining_life_km"] = (
        (cleaned["remaining_life_pred"] / 100.0) * SAFE_TIRE_LIFE_KM
    ).round(0)
    cleaned["health_norm"] = (cleaned["health_score"] / 10.0).astype(np.float32)
    cleaned["remaining_life_norm"] = (cleaned["remaining_life_km"] / SAFE_TIRE_LIFE_KM).astype(np.float32)
    cleaned["replacement_urgency"] = cleaned["remaining_life_pred"].apply(replacement_urgency)
    cleaned["risk_score"] = cleaned.apply(compute_risk_score, axis=1)
    cleaned["risk_level"] = cleaned["risk_score"].apply(risk_label)
    cleaned["replace_recommended"] = cleaned["replacement_urgency"].isin(["High", "Immediate"]) | (
        cleaned["risk_level"].isin(["HIGH", "CRITICAL"])
    )

    old_tire = cleaned["manufacture_year"].notna() & (
        datetime.now().year - cleaned["manufacture_year"].fillna(datetime.now().year).astype(int) > 5
    )
    cleaned.loc[old_tire, "health_score"] = (cleaned.loc[old_tire, "health_score"] * 0.9).round(2)
    cleaned["health_norm"] = (cleaned["health_score"] / 10.0).astype(np.float32)

    return cleaned


def build_image_index(images_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not images_dir.exists():
        return index
    for image_path in sorted(images_dir.rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        keys = {
            image_path.name.lower(),
            image_path.stem.lower(),
            normalize_image_key(image_path.name),
            normalize_image_key(image_path.stem),
        }
        for key in keys:
            if key:
                index.setdefault(key, image_path)
    return index


def merge_image_indexes(*indexes: dict[str, Path]) -> dict[str, Path]:
    merged: dict[str, Path] = {}
    for index in indexes:
        for key, value in index.items():
            merged.setdefault(key, value)
    return merged


def match_image(
    reference: object,
    image_index: dict[str, Path],
    search_roots: list[Path] | None = None,
) -> Path | None:
    if pd.isna(reference):
        return None
    text = str(reference).strip()
    if not text:
        return None

    candidate = Path(text)
    if candidate.is_file():
        return candidate
    for root in search_roots or []:
        rooted = root / text
        if rooted.is_file():
            return rooted

    path_name = Path(text).name
    for key in (
        text.lower(),
        path_name.lower(),
        Path(text).stem.lower(),
        Path(path_name).stem.lower(),
        normalize_image_key(text),
        normalize_image_key(path_name),
    ):
        if key in image_index:
            return image_index[key]
    return None


def ensure_safe_generated_path(path: Path, dataset_root: Path) -> None:
    resolved_root = dataset_root.resolve()
    resolved_path = path.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ValueError(f"Refusing to rebuild path outside dataset root: {path}")
    raw_dir = (dataset_root / "raw").resolve()
    if resolved_path == raw_dir or raw_dir in resolved_path.parents:
        raise ValueError(f"Refusing to rebuild raw data path: {path}")


def rebuild_dir(path: Path, dataset_root: Path) -> None:
    ensure_safe_generated_path(path, dataset_root)
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def ensure_dirs(paths: DatasetPaths) -> None:
    for path in [paths.processed_dir, paths.labels_dir, paths.annotations_dir, paths.metadata_dir, paths.splits_dir]:
        path.mkdir(parents=True, exist_ok=True)
    for path in [
        paths.images_dir / "front_view",
        paths.images_dir / "sidewall",
        paths.images_dir / "side_view",
        paths.images_dir / "closeup",
        paths.multi_view_dir / "train",
        paths.multi_view_dir / "val",
        paths.multi_view_dir / "validation",
        paths.multi_view_dir / "test",
        paths.labels_dir / "tread_depth",
        paths.labels_dir / "tire_health",
        paths.labels_dir / "wear_pattern",
    ]:
        rebuild_dir(path, paths.root)


def copy_image(src: Path | None, dst_dir: Path, prefix: str = "") -> str:
    if src is None:
        return ""
    target_name = f"{prefix}{src.name}" if prefix else src.name
    target = dst_dir / target_name
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        counter = 2
        while target.exists():
            target = dst_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.copy2(src, target)
    return str(target)


def attach_and_copy_images(df: pd.DataFrame, paths: DatasetPaths) -> pd.DataFrame:
    front_index = merge_image_indexes(
        build_image_index(paths.raw_front_images_dir),
        build_image_index(paths.learning_front_images_dir),
        build_image_index(paths.continuous_front_images_dir),
        build_image_index(paths.tread_images_dir),
    )
    side_index = merge_image_indexes(
        build_image_index(paths.raw_sidewall_images_dir),
        build_image_index(paths.learning_sidewall_images_dir),
        build_image_index(paths.sidewall_images_dir),
    )
    front_output = paths.images_dir / "front_view"
    side_output = paths.images_dir / "sidewall"
    front_output.mkdir(parents=True, exist_ok=True)
    side_output.mkdir(parents=True, exist_ok=True)

    enriched = df.copy()
    front_sources: list[str] = []
    side_sources: list[str] = []
    front_copies: list[str] = []
    side_copies: list[str] = []

    for row in enriched.itertuples(index=False):
        front_src = None
        for reference in (
            getattr(row, "front_image_reference", ""),
            getattr(row, "image_id"),
        ):
            front_src = match_image(
                reference,
                front_index,
                [
                    paths.raw_front_images_dir,
                    paths.learning_front_images_dir,
                    paths.continuous_front_images_dir,
                    paths.tread_images_dir,
                    paths.raw_dir,
                    paths.root,
                ],
            )
            if front_src is not None:
                break
        side_src = match_image(
            getattr(row, "sidewall_image_id"),
            side_index,
            [
                paths.raw_sidewall_images_dir,
                paths.learning_sidewall_images_dir,
                paths.sidewall_images_dir,
                paths.raw_dir,
                paths.root,
            ],
        )
        if side_src is None:
            side_src = match_image(
                getattr(row, "image_id"),
                side_index,
                [
                    paths.raw_sidewall_images_dir,
                    paths.learning_sidewall_images_dir,
                    paths.sidewall_images_dir,
                    paths.raw_dir,
                    paths.root,
                ],
            )
        front_sources.append(str(front_src) if front_src else "")
        side_sources.append(str(side_src) if side_src else "")
        front_copies.append(copy_image(front_src, front_output))
        side_copies.append(copy_image(side_src, side_output))

    enriched["front_image_path"] = front_sources
    enriched["sidewall_image_path"] = side_sources
    enriched["image_path"] = front_sources
    enriched["dataset_front_path"] = front_copies
    enriched["dataset_sidewall_path"] = side_copies
    enriched["has_image"] = enriched["front_image_path"] != ""
    enriched["has_sidewall_image"] = enriched["sidewall_image_path"] != ""
    enriched["feature_tread_spread"] = (enriched["tread_1"] - enriched["tread_4"]).abs().astype(np.float32)
    enriched["feature_center_edge_gap"] = (
        ((enriched["tread_2"] + enriched["tread_3"]) / 2.0)
        - ((enriched["tread_1"] + enriched["tread_4"]) / 2.0)
    ).astype(np.float32)
    return enriched


def split_dataset(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    def with_val_alias(
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        val_df = val_df.reset_index(drop=True)
        return {
            "train": train_df.reset_index(drop=True),
            "val": val_df,
            "validation": val_df.copy(),
            "test": test_df.reset_index(drop=True),
        }

    if len(df) < 3:
        return with_val_alias(df, df.iloc[0:0].copy(), df.iloc[0:0].copy())

    stratify = df["condition"] if df["condition"].value_counts().min() >= 2 else None
    train_test_split = _load_train_test_split()
    if train_test_split is not None:
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
            return with_val_alias(train_df, val_df, test_df)
        except ValueError:
            pass

    shuffled = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    train_end = max(1, int(len(shuffled) * 0.70))
    val_end = min(len(shuffled), train_end + max(1, int(len(shuffled) * 0.15)))
    return with_val_alias(
        shuffled.iloc[:train_end],
        shuffled.iloc[train_end:val_end],
        shuffled.iloc[val_end:],
    )


def write_json_records(df: pd.DataFrame, out_dir: Path, columns: list[str]) -> None:
    used_names: set[str] = set()
    for index, row in enumerate(df[columns].to_dict(orient="records")):
        image_id = str(row["image_id"])
        safe_stem = normalize_image_key(Path(image_id).stem) or normalize_image_key(image_id)
        if not safe_stem:
            safe_stem = f"row_{index:06d}"
        if safe_stem in used_names:
            safe_stem = f"{safe_stem}_{index:06d}"
        used_names.add(safe_stem)
        out_path = out_dir / f"{safe_stem}.json"
        out_path.write_text(json.dumps(row, indent=2, default=str), encoding="utf-8")


def write_label_outputs(df: pd.DataFrame, paths: DatasetPaths) -> None:
    tread_df = df[
        [
            "image_id",
            "tread_1",
            "tread_2",
            "tread_3",
            "tread_4",
            "tread_average",
            "brand",
            "tire_size",
            "condition",
            "manufacture_year",
        ]
    ].copy()
    tread_df["tread_depth_class"] = tread_df["tread_average"].apply(tread_depth_class)
    tread_df.to_csv(paths.labels_dir / "tread_depth.csv", index=False)

    health_df = df[
        [
            "image_id",
            "health_score",
            "remaining_life_km",
            "remaining_life_pred",
            "risk_score",
            "risk_level",
            "replacement_urgency",
            "replace_recommended",
        ]
    ].copy()
    health_df.to_csv(paths.labels_dir / "tire_health.csv", index=False)

    wear_df = df[["image_id", "wear_pattern", "wear_class_6", "condition"]].copy()
    wear_df = wear_df.rename(columns={"wear_class_6": "class_id"})
    wear_df["severity"] = [wear_severity(pattern, condition) for pattern, condition in zip(wear_df["wear_pattern"], wear_df["condition"])]
    wear_df["cause"] = wear_df["wear_pattern"].map(
        {
            "even": "Normal wear",
            "center_wear": "Possible overinflation",
            "edge_wear": "Possible underinflation",
            "one_sided_wear": "Possible alignment issue",
            "uneven_wear": "Irregular tread readings",
            "critical_wear": "Tread below safe threshold",
        }
    )
    wear_df["corrective_action"] = wear_df["severity"].map(
        {"low": "Continue monitoring", "moderate": "Inspect pressure and alignment", "high": "Replace or inspect immediately"}
    )
    wear_df.to_csv(paths.labels_dir / "wear_pattern.csv", index=False)

    write_json_records(tread_df, paths.labels_dir / "tread_depth", list(tread_df.columns))
    write_json_records(health_df, paths.labels_dir / "tire_health", list(health_df.columns))
    write_json_records(wear_df, paths.labels_dir / "wear_pattern", list(wear_df.columns))


def write_annotation_outputs(df: pd.DataFrame, paths: DatasetPaths) -> None:
    cnn_df = df[
        [
            "image_id",
            "front_image_path",
            "wear_class_6",
            "wear_pattern",
            "tread_average",
            "has_image",
            "feature_tread_spread",
            "feature_center_edge_gap",
        ]
    ].copy()
    cnn_df = cnn_df.rename(
        columns={
            "front_image_path": "image_path",
            "wear_class_6": "wear_class",
            "wear_pattern": "wear_label",
            "tread_average": "tread_depth_mm",
        }
    )
    cnn_df["crack_detected"] = 0
    cnn_df["groove_visible"] = cnn_df["has_image"]
    cnn_df["surface_texture"] = np.where(cnn_df["wear_label"] == "even", "smooth", "uneven")
    cnn_df["confidence"] = np.where(cnn_df["has_image"], 0.95, 0.35)
    cnn_df.drop(columns=["has_image"]).to_csv(paths.annotations_dir / "cnn_labels.csv", index=False)

    ann_df = df[
        [
            "image_id",
            "tread_average",
            "health_score",
            "remaining_life_pred",
            "wear_pattern",
            "risk_level",
            "replacement_urgency",
        ]
    ].copy()
    ann_df = ann_df.rename(
        columns={
            "tread_average": "tread_depth_pred",
            "health_score": "health_score_pred",
            "wear_pattern": "wear_pattern_pred",
        }
    )
    ann_df.to_csv(paths.annotations_dir / "ann_labels.csv", index=False)

    ocr_df = df[
        [
            "image_id",
            "sidewall_image_path",
            "brand",
            "tire_size",
            "manufacture_week",
            "manufacture_year",
            "ocr_confidence",
        ]
    ].copy()
    ocr_df = ocr_df.rename(columns={"brand": "brand_cleaned", "tire_size": "tire_size_cleaned"})
    ocr_df["brand_raw"] = ocr_df["brand_cleaned"]
    ocr_df["tire_size_raw"] = ocr_df["tire_size_cleaned"]
    ocr_df = ocr_df[
        [
            "image_id",
            "sidewall_image_path",
            "brand_raw",
            "brand_cleaned",
            "tire_size_raw",
            "tire_size_cleaned",
            "manufacture_week",
            "manufacture_year",
            "ocr_confidence",
        ]
    ]
    ocr_df.to_csv(paths.annotations_dir / "ocr_labels.csv", index=False)


def write_splits_and_multiview(splits: dict[str, pd.DataFrame], paths: DatasetPaths) -> None:
    for split_name, split_df in splits.items():
        split_dir = paths.splits_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        split_df.to_csv(split_dir / "labels.csv", index=False)

        view_dir = paths.multi_view_dir / split_name
        view_dir.mkdir(parents=True, exist_ok=True)
        (view_dir / "front_view").mkdir(parents=True, exist_ok=True)
        (view_dir / "sidewall").mkdir(parents=True, exist_ok=True)
        (view_dir / "side_view").mkdir(parents=True, exist_ok=True)
        split_df.to_csv(view_dir / "labels.csv", index=False)

        for row in split_df.itertuples(index=False):
            image_key = normalize_image_key(getattr(row, "image_id")) or Path(str(getattr(row, "image_id"))).stem
            front_value = str(getattr(row, "dataset_front_path", "") or "")
            side_value = str(getattr(row, "dataset_sidewall_path", "") or "")
            front_path = Path(front_value) if front_value else None
            side_path = Path(side_value) if side_value else None
            if front_path is not None and front_path.is_file():
                shutil.copy2(front_path, view_dir / "front_view" / f"{image_key}{front_path.suffix}")
            if side_path is not None and side_path.is_file():
                shutil.copy2(side_path, view_dir / "sidewall" / f"{image_key}{side_path.suffix}")
                shutil.copy2(side_path, view_dir / "side_view" / f"{image_key}{side_path.suffix}")


def write_manifest(
    df: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
    paths: DatasetPaths,
    source_labels: Path,
) -> dict[str, Any]:
    val_count = int(len(splits["val"]))
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_labels": str(source_labels),
        "spreadsheet": str(source_labels) if source_labels.suffix.lower() in {".xlsx", ".xls"} else "",
        "raw_labels": str(source_labels) if source_labels.suffix.lower() == ".csv" else "",
        "learning_labels": [
            str(path)
            for path in (paths.learning_labels_csv, paths.continuous_learning_labels_csv)
            if path.exists()
        ],
        "row_counts": {
            "raw_rows_after_normalization": int(len(df)),
            "processed_rows": int(len(df)),
            "train_rows": int(len(splits["train"])),
            "val_rows": val_count,
            "validation_rows": val_count,
            "test_rows": int(len(splits["test"])),
        },
        "image_matching": {
            "front_matched": int(df["has_image"].sum()),
            "front_unmatched": int((~df["has_image"]).sum()),
            "sidewall_matched": int(df["has_sidewall_image"].sum()),
            "sidewall_unmatched": int((~df["has_sidewall_image"]).sum()),
        },
        "distributions": {
            "condition": df["condition"].value_counts().to_dict(),
            "wear_pattern": df["wear_pattern"].value_counts().to_dict(),
            "risk_level": df["risk_level"].value_counts().to_dict(),
        },
        "outputs": {
            "processed_labels": str(paths.labels_csv),
            "cleaned_dataset": str(paths.cleaned_csv),
            "features": str(paths.features_csv),
            "labels_dir": str(paths.labels_dir),
            "annotations_dir": str(paths.annotations_dir),
            "images_dir": str(paths.images_dir),
            "multi_view_dir": str(paths.multi_view_dir),
            "splits_dir": str(paths.splits_dir),
            "manifest": str(paths.manifest_json),
        },
    }
    paths.manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def find_source_labels(
    paths: DatasetPaths,
    spreadsheet: Path | None,
    labels_csv: Path | None,
) -> Path:
    if labels_csv is not None:
        return labels_csv
    if spreadsheet is not None:
        return spreadsheet
    if paths.raw_labels_csv.exists():
        return paths.raw_labels_csv
    return newest_spreadsheet(paths.spreadsheet_dir)


def read_source_labels(source_path: Path) -> pd.DataFrame:
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source_path)
    raise ValueError(f"Unsupported label file type: {source_path}")


def prepare_dataset(
    paths: DatasetPaths = DatasetPaths(),
    spreadsheet: Path | None = None,
    labels_csv: Path | None = None,
) -> dict[str, Any]:
    ensure_dirs(paths)
    source_labels = find_source_labels(paths, spreadsheet, labels_csv)
    raw_df = read_source_labels(source_labels)
    base_df = normalize_spreadsheet_columns(raw_df)
    learning_frames = load_learning_label_frames(paths)
    if learning_frames:
        base_df = pd.concat([base_df, *learning_frames], ignore_index=True)
    cleaned_df = clean_and_enrich(base_df)

    labels_df = cleaned_df[[column for column in BASE_LABEL_COLUMNS if column in cleaned_df.columns]].copy()
    labels_df.to_csv(paths.labels_csv, index=False)

    cleaned_df.to_csv(paths.cleaned_csv, index=False)
    features_df = attach_and_copy_images(cleaned_df, paths)
    features_df = features_df[[column for column in FEATURE_COLUMNS if column in features_df.columns]]
    features_df.to_csv(paths.features_csv, index=False)

    write_label_outputs(features_df, paths)
    write_annotation_outputs(features_df, paths)
    splits = split_dataset(features_df)
    write_splits_and_multiview(splits, paths)
    return write_manifest(features_df, splits, paths, source_labels)


def print_summary(manifest: dict[str, Any]) -> None:
    rows = manifest["row_counts"]
    matching = manifest["image_matching"]
    print("")
    print("=" * 72)
    print("SMART TIRE DATASET PREPARATION COMPLETE")
    print("=" * 72)
    print(f"Processed rows:       {rows['processed_rows']}")
    print(
        "Splits:               "
        f"train={rows['train_rows']} val={rows['val_rows']} test={rows['test_rows']}"
    )
    print(f"Front images matched: {matching['front_matched']} matched, {matching['front_unmatched']} unmatched")
    print(
        "Sidewall matched:     "
        f"{matching['sidewall_matched']} matched, {matching['sidewall_unmatched']} unmatched"
    )
    print(f"Manifest:             {manifest['outputs']['manifest']}")
    print("=" * 72)
    print("")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare generated dataset artifacts from raw tire data")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DATASET_DIR,
        help="Dataset root directory. Defaults to dataset/ under the project root.",
    )
    parser.add_argument(
        "--spreadsheet",
        type=Path,
        default=None,
        help="Optional explicit spreadsheet path. Defaults to the newest .xlsx in dataset/raw/spreadsheet.",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help="Optional explicit CSV labels path. Defaults to dataset/raw/labels.csv when present.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = DatasetPaths(root=args.dataset_root)
    manifest = prepare_dataset(paths=paths, spreadsheet=args.spreadsheet, labels_csv=args.labels)
    print_summary(manifest)


if __name__ == "__main__":
    main()
