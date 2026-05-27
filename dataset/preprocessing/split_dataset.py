"""
Dataset Splitter — Creates stratified train/val/test splits.
Stratification ensures balanced wear pattern distribution across splits.

New dataset layout:
  Input:  dataset/processed/cleaned_dataset.csv
  Images: dataset/raw/tread_images/{safe,moderate,replace}/
  Output: dataset/splits/{train,validation,test}/labels.csv
"""

import pandas as pd
import numpy as np
import shutil
import logging
from pathlib import Path
from typing import Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("dataset")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_IMAGES_DIR = DATA_DIR / "raw" / "tread_images"
SPLITS_DIR = DATA_DIR / "splits"

TRAIN_SPLIT = 0.80
VAL_SPLIT = 0.10
TEST_SPLIT = 0.10
RANDOM_SEED = 42


def stratified_split(
    df: pd.DataFrame,
    stratify_col: str = "wear_pattern",
    train: float = TRAIN_SPLIT,
    val: float = VAL_SPLIT,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Perform stratified train/val/test split.

    Args:
        df: Full dataset DataFrame
        stratify_col: Column to stratify by (ensures balanced class distribution)
        train, val: Split fractions (test = 1 - train - val)
        seed: Random seed for reproducibility

    Returns:
        (train_df, val_df, test_df)
    """
    np.random.seed(seed)

    if stratify_col not in df.columns:
        logger.warning(f"Stratify column '{stratify_col}' not found — using random split")
        idx = np.random.permutation(len(df))
        n_train = int(len(df) * train)
        n_val = int(len(df) * val)
        return (
            df.iloc[idx[:n_train]].reset_index(drop=True),
            df.iloc[idx[n_train:n_train + n_val]].reset_index(drop=True),
            df.iloc[idx[n_train + n_val:]].reset_index(drop=True),
        )

    train_dfs, val_dfs, test_dfs = [], [], []

    for cls in df[stratify_col].unique():
        subset = df[df[stratify_col] == cls].sample(frac=1, random_state=seed)
        n = len(subset)
        n_train = int(n * train)
        n_val = int(n * val)

        train_dfs.append(subset.iloc[:n_train])
        val_dfs.append(subset.iloc[n_train:n_train + n_val])
        test_dfs.append(subset.iloc[n_train + n_val:])

    train_df = pd.concat(train_dfs).sample(frac=1, random_state=seed).reset_index(drop=True)
    val_df = pd.concat(val_dfs).sample(frac=1, random_state=seed).reset_index(drop=True)
    test_df = pd.concat(test_dfs).sample(frac=1, random_state=seed).reset_index(drop=True)

    return train_df, val_df, test_df


def split_and_save(
    labels_csv: str = str(PROCESSED_DIR / "cleaned_dataset.csv"),
    images_dir: str = str(RAW_IMAGES_DIR),
    output_dir: str = str(SPLITS_DIR),
):
    """
    Load cleaned labels, split into train/val/test, copy images to split directories.

    Input:  dataset/processed/cleaned_dataset.csv
    Images: dataset/raw/tread_images/ (condition sub-folders: safe/moderate/replace)
    Output: dataset/splits/{train,validation,test}/labels.csv
    """
    if not Path(labels_csv).exists():
        logger.error(f"Labels CSV not found: {labels_csv}")
        logger.info("Please run clean_dataset.py first")
        return

    df = pd.read_csv(labels_csv)
    logger.info(f"Total dataset: {len(df)} samples")

    train_df, val_df, test_df = stratified_split(df)

    # Save split CSVs and copy images
    output_dir_path = Path(output_dir)
    images_path = Path(images_dir)
    for split_name, split_df in [("train", train_df), ("validation", val_df), ("test", test_df)]:
        split_dir = output_dir_path / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        csv_path = split_dir / "labels.csv"
        split_df.to_csv(csv_path, index=False)
        logger.info(f"{split_name}: {len(split_df)} samples → {csv_path}")

        # Copy images from condition sub-folders to split directory
        if images_path.exists() and "image_id" in split_df.columns:
            images_copied = 0
            for _, row in split_df.iterrows():
                image_id = str(row["image_id"])
                condition = str(row.get("condition", ""))
                for ext in (".jpg", ".jpeg", ".png"):
                    # Search in condition sub-folder first, then root
                    candidates = [
                        images_path / condition / f"{image_id}{ext}",
                        images_path / f"{image_id}{ext}",
                    ]
                    for src in candidates:
                        if src.exists():
                            dst = split_dir / src.name
                            if not dst.exists():
                                shutil.copy2(src, dst)
                                images_copied += 1
                            break
            logger.info(f"  Copied {images_copied} images for {split_name} split")

    # Summary
    print("\n=== Split Summary ===")
    print(f"Train:      {len(train_df):>5} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"Validation: {len(val_df):>5} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"Test:       {len(test_df):>5} ({len(test_df)/len(df)*100:.1f}%)")


if __name__ == "__main__":
    split_and_save()
