"""
Dataset Cleaning Script — Fixes known data quality issues:
  1. Tread 4 = 0.0 readings (sensor missing) → imputed from T1-T3 average
  2. Brand name normalization (Michilen → Michelin, etc.)
  3. Remove duplicate image entries
  4. Fix tire size formatting (185/65R15 → 185/65 R15)

New dataset layout:
  dataset/raw/spreadsheet/dataset.xlsx  ← raw source
  dataset/processed/cleaned_dataset.csv  ← output of this script
  dataset/processed/labels.csv           ← merged label file
"""

import pandas as pd
import numpy as np
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("dataset")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
SPREADSHEET_DIR = RAW_DIR / "spreadsheet"


BRAND_CORRECTIONS = {
    "michilen": "Michelin",
    "michelino": "Michelin",
    "bridgeston": "Bridgestone",
    "bridgstone": "Bridgestone",
    "goodyer": "Goodyear",
    "good year": "Goodyear",
    "continetal": "Continental",
    "pireli": "Pirelli",
    "pirelly": "Pirelli",
    "yokohamma": "Yokohama",
    "dunlop tires": "Dunlop",
    "BF goodrich": "BF Goodrich",
}


def fix_tread_zeros(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace Tread 4 = 0.0 with average of T1, T2, T3.
    Known dataset issue: some tire gauges failed to record T4.
    """
    t4_zero_mask = df["tread_4"] == 0.0
    n_fixed = t4_zero_mask.sum()

    if n_fixed > 0:
        df.loc[t4_zero_mask, "tread_4"] = df.loc[t4_zero_mask, ["tread_1", "tread_2", "tread_3"]].mean(axis=1)
        logger.info(f"Fixed {n_fixed} rows with Tread 4 = 0.0")

    # Also fix any other zeros
    for col in ["tread_1", "tread_2", "tread_3"]:
        zero_mask = df[col] == 0.0
        if zero_mask.sum() > 0:
            other_cols = [c for c in ["tread_1","tread_2","tread_3","tread_4"] if c != col]
            df.loc[zero_mask, col] = df.loc[zero_mask, other_cols].mean(axis=1)
            logger.info(f"Fixed {zero_mask.sum()} zeros in {col}")

    # Recompute average
    df["tread_average"] = df[["tread_1", "tread_2", "tread_3", "tread_4"]].mean(axis=1)

    # Validate range
    for col in ["tread_1", "tread_2", "tread_3", "tread_4"]:
        out_of_range = (df[col] < 0.0) | (df[col] > 12.0)
        if out_of_range.sum() > 0:
            logger.warning(f"{out_of_range.sum()} out-of-range values in {col} — clamping")
            df[col] = df[col].clip(0.0, 12.0)

    return df


def normalize_brand_names(df: pd.DataFrame, col: str = "brand") -> pd.DataFrame:
    """
    Normalize tire brand names to canonical spelling.
    Handles common OCR errors and abbreviations.
    """
    if col not in df.columns:
        logger.warning(f"Column '{col}' not found — skipping brand normalization")
        return df

    original_count = df[col].nunique()

    def clean_brand(name: str) -> str:
        if pd.isna(name):
            return "Unknown"
        name = str(name).strip()
        lower = name.lower()
        for wrong, correct in BRAND_CORRECTIONS.items():
            if lower == wrong.lower():
                return correct
        # Title case for unrecognized brands
        return name.title()

    df[col] = df[col].apply(clean_brand)
    new_count = df[col].nunique()
    logger.info(f"Brand normalization: {original_count} → {new_count} unique brands")
    return df


def fix_tire_size_format(df: pd.DataFrame, col: str = "tire_size") -> pd.DataFrame:
    """
    Standardize tire size to '185/65 R15' format.
    Handles: '185/65R15', '185/65r15', '18565R15', etc.
    """
    if col not in df.columns:
        return df

    def parse_size(s: str) -> str:
        if pd.isna(s):
            return "Unknown"
        s = str(s).strip().upper()
        # Pattern: WIDTHxxAspectRDiameter
        m = re.match(r"(\d{3})[/\\-]?(\d{2})\s*[Rr]\s*(\d{2})", s)
        if m:
            return f"{m.group(1)}/{m.group(2)} R{m.group(3)}"
        return s

    df[col] = df[col].apply(parse_size)
    return df


def remove_duplicates(df: pd.DataFrame, id_col: str = "image_id") -> pd.DataFrame:
    """Remove duplicate image entries based on image ID."""
    before = len(df)
    df = df.drop_duplicates(subset=[id_col] if id_col in df.columns else None)
    after = len(df)
    if before > after:
        logger.info(f"Removed {before - after} duplicate rows")
    return df


def clean_dataset(
    input_csv: str = str(PROCESSED_DIR / "labels.csv"),
    output_csv: str = str(PROCESSED_DIR / "cleaned_dataset.csv"),
):
    """
    Main dataset cleaning pipeline.

    Reads raw labels from dataset/processed/labels.csv (or dataset.xlsx
    converted to CSV) and produces dataset/processed/cleaned_dataset.csv.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Try xlsx first if CSV is empty / missing
    xlsx_path = SPREADSHEET_DIR / "dataset.xlsx"
    if not Path(input_csv).exists() or Path(input_csv).stat().st_size < 10:
        if xlsx_path.exists():
            logger.info(f"Loading from Excel: {xlsx_path}")
            df = pd.read_excel(xlsx_path)
            df.to_csv(input_csv, index=False)
            logger.info(f"Converted xlsx → {input_csv}")
        else:
            logger.error(f"Input not found: {input_csv} or {xlsx_path}")
            logger.info("Creating sample dataset template...")
            _create_sample_template(input_csv)
            return
    else:
        logger.info(f"Loading dataset from: {input_csv}")

    df = pd.read_csv(input_csv)
    logger.info(f"Loaded {len(df)} rows, {df.shape[1]} columns")

    # Apply cleaning steps
    df = remove_duplicates(df)
    df = fix_tread_zeros(df)
    df = normalize_brand_names(df, col="brand")
    df = fix_tire_size_format(df, col="tire_size")

    # Save cleaned dataset
    df.to_csv(output_csv, index=False)
    logger.info(f"Cleaned dataset saved: {output_csv} ({len(df)} rows)")

    # Print summary
    print("\n=== Dataset Summary ===")
    print(f"Total samples: {len(df)}")
    print(f"Average tread depth: {df.get('tread_average', pd.Series()).mean():.2f}mm")
    if "brand" in df.columns:
        print(f"Unique brands: {df['brand'].nunique()}")
    return df


def _create_sample_template(path: str):
    """Create a sample CSV template for labels data."""
    import os
    os.makedirs(Path(path).parent, exist_ok=True)
    sample = pd.DataFrame({
        "image_id": ["tire_001", "tire_002", "tire_003"],
        "tread_1": [7.2, 3.1, 1.4],
        "tread_2": [7.0, 3.4, 1.5],
        "tread_3": [6.8, 3.0, 1.3],
        "tread_4": [0.0, 3.2, 1.6],   # Note: T4 = 0 is a known sensor issue
        "tread_average": [0.0, 3.175, 1.45],
        "brand": ["michilen", "Bridgestone", "Goodyear"],
        "tire_model": ["Primacy 4", "Turanza T005", "EfficientGrip"],
        "tire_size": ["185/65R15", "205/55r17", "195/60 R15"],
        "manufacture_year": [2022, 2020, 2019],
        "condition": ["safe", "moderate", "replace"],
        "wear_pattern": ["even", "center_wear", "edge_wear"],
        "health_score": [9.2, 5.5, 1.8],
        "remaining_life_km": [65000, 25000, 3000],
    })
    sample.to_csv(path, index=False)
    logger.info(f"Sample template created: {path}")


if __name__ == "__main__":
    clean_dataset()
