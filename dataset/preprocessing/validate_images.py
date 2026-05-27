"""
Validate Images Script — Check all images in dataset/raw/tread_images/ for:
1. Readable (not corrupted)
2. Min resolution (224×224 px)
3. Color mode (RGB)
4. File size (not empty, not >20MB)
5. Not duplicate hashes

Images live in condition sub-folders:
  dataset/raw/tread_images/safe/
  dataset/raw/tread_images/moderate/
  dataset/raw/tread_images/replace/

Run before training: python dataset/preprocessing/validate_images.py
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Tuple, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

IMAGES_DIR = Path("dataset/raw/tread_images")
MIN_WIDTH = 224
MIN_HEIGHT = 224
MAX_FILE_MB = 20.0


def validate_image(image_path: Path) -> Tuple[bool, str]:
    """
    Validate a single image file.

    Returns:
        (is_valid: bool, reason: str)
    """
    try:
        import cv2
        import numpy as np

        # File size check
        size_mb = image_path.stat().st_size / (1024 * 1024)
        if size_mb == 0:
            return False, "Empty file"
        if size_mb > MAX_FILE_MB:
            return False, f"File too large ({size_mb:.1f}MB > {MAX_FILE_MB}MB)"

        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            return False, "cv2 could not decode image — likely corrupted"

        # Dimensions check
        h, w = img.shape[:2]
        if h < MIN_HEIGHT or w < MIN_WIDTH:
            return False, f"Resolution too small ({w}×{h} < {MIN_WIDTH}×{MIN_HEIGHT})"

        # Channel check
        if len(img.shape) < 3 or img.shape[2] < 3:
            return False, f"Not a color (RGB) image — shape: {img.shape}"

        # Blank/uniform image check
        std = float(img.std())
        if std < 2.0:
            return False, f"Image appears blank or nearly uniform (std={std:.2f})"

        return True, "OK"

    except PermissionError:
        return False, "Permission denied"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def find_duplicates(image_paths: List[Path]) -> List[Tuple[Path, Path]]:
    """Find duplicate images by MD5 hash of first 512KB."""
    seen = {}
    duplicates = []
    for path in image_paths:
        try:
            with open(path, "rb") as f:
                partial = f.read(512 * 1024)
            hash_val = hashlib.md5(partial).hexdigest()
            if hash_val in seen:
                duplicates.append((seen[hash_val], path))
            else:
                seen[hash_val] = path
        except Exception:
            pass
    return duplicates


def validate_all(images_dir: str = str(IMAGES_DIR)) -> dict:
    """
    Validate all images in the dataset directory.
    Returns summary statistics.
    """
    images_dir = Path(images_dir)
    if not images_dir.exists():
        logger.warning(f"Images directory not found: {images_dir}")
        images_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created empty images directory")
        return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    # Find all image files
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = [
        f for f in images_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in extensions
    ]

    if not image_files:
        logger.warning(f"No images found in {images_dir}")
        return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    logger.info(f"Validating {len(image_files)} images...")

    valid_count = 0
    errors = []

    for img_path in image_files:
        is_valid, reason = validate_image(img_path)
        if is_valid:
            valid_count += 1
        else:
            errors.append({"file": str(img_path.name), "reason": reason})
            logger.warning(f"  ❌ {img_path.name}: {reason}")

    # Check duplicates
    duplicates = find_duplicates(image_files)
    for orig, dup in duplicates:
        logger.warning(f"  ⚠️  Duplicate: {dup.name} == {orig.name}")

    invalid_count = len(errors)
    logger.info(f"\nValidation complete:")
    logger.info(f"  ✅ Valid:    {valid_count}/{len(image_files)}")
    logger.info(f"  ❌ Invalid:  {invalid_count}")
    logger.info(f"  ⚠️  Duplicates: {len(duplicates)}")

    if invalid_count > 0:
        logger.info("\nInvalid files (remove or fix before training):")
        for e in errors[:20]:
            logger.info(f"  {e['file']}: {e['reason']}")

    return {
        "total": len(image_files),
        "valid": valid_count,
        "invalid": invalid_count,
        "duplicates": len(duplicates),
        "errors": errors,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate tire dataset images")
    parser.add_argument("--dir", default=str(IMAGES_DIR), help="Images directory")
    args = parser.parse_args()

    results = validate_all(args.dir)
    if results["invalid"] > 0:
        import sys
        sys.exit(1)  # Non-zero exit for CI/CD
