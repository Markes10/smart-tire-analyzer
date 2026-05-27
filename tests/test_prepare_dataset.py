from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.prepare_dataset import (
    DatasetPaths,
    attach_and_copy_images,
    build_image_index,
    clean_and_enrich,
    clean_brand,
    clean_tire_size,
    extract_dot_date,
    match_image,
    normalize_spreadsheet_columns,
    prepare_dataset,
    repair_tread_depths,
)


def _make_dataset_root(tmp_path: Path) -> Path:
    root = tmp_path / "dataset"
    (root / "raw" / "spreadsheet").mkdir(parents=True)
    (root / "raw" / "tread_images").mkdir(parents=True)
    (root / "raw" / "sidewall_images" / "Goodyear").mkdir(parents=True)
    return root


def _sample_raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Front Profile": [
                "IMG_001 - Viren Viren.jpg",
                "IMG_002 - Viren Viren.jpg",
                "IMG_003 - Viren Viren.jpg",
            ],
            "Side Profile URL": [
                "SIDE_001 - Viren Viren",
                "SIDE_002 - Viren Viren",
                "SIDE_003 - Viren Viren",
            ],
            "Tread 1": [7.0, 3.0, 1.0],
            "Tread 2": [7.2, 3.2, 1.2],
            "Tread 3": [7.1, 3.1, 1.1],
            "Tread 4": [0.0, 3.3, 1.3],
            "Average form": [0.0, 3.15, 1.15],
            "Company name": ["goodyer", "MRF", "michilen"],
            "model": ["Assurance", "ZLX", "Primacy"],
            "Tire Size": ["215/60R16", "155/65 R15", "18565R15"],
            "DOT & DOM": ["DOT 2524", "DOT 0121", ""],
            "TUBE/TUBELESS": ["TUBELESS", "TUBE", "TUBELESS"],
        }
    )


def test_normalize_spreadsheet_columns_maps_form_headers():
    normalized = normalize_spreadsheet_columns(_sample_raw_frame())
    assert "image_id" in normalized.columns
    assert "sidewall_image_id" in normalized.columns
    assert "tread_1" in normalized.columns
    assert "ocr_text" in normalized.columns
    assert normalized.loc[0, "image_id"] == "IMG_001 - Viren Viren.jpg"


def test_dot_extraction_from_dot_text():
    week, year = extract_dot_date("DOT 2524")
    assert week == 25
    assert year == 2024


def test_tread_average_and_zero_repair():
    normalized = normalize_spreadsheet_columns(_sample_raw_frame().iloc[[0]])
    repaired = repair_tread_depths(normalized)
    assert repaired.loc[0, "tread_4"] == pytest.approx((7.0 + 7.2 + 7.1) / 3)
    assert repaired.loc[0, "tread_average"] == pytest.approx(
        repaired.loc[0, ["tread_1", "tread_2", "tread_3", "tread_4"]].mean()
    )


def test_brand_and_tire_size_cleaning():
    assert clean_brand("goodyer") == "Goodyear"
    assert clean_brand("michilen") == "Michelin"
    assert clean_tire_size("18565R15") == "185/65 R15"
    assert clean_tire_size("215/60R16") == "215/60 R16"


def test_image_matching_with_missing_extension(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "SIDE_001 - Viren Viren.JPG"
    image_path.write_bytes(b"fake image")
    index = build_image_index(image_dir)
    assert match_image("SIDE_001 - Viren Viren", index) == image_path


def test_attach_and_copy_images_leaves_raw_untouched(tmp_path: Path):
    root = _make_dataset_root(tmp_path)
    paths = DatasetPaths(root=root)
    raw_front = root / "raw" / "tread_images" / "IMG_001 - Viren Viren.jpg"
    raw_side = root / "raw" / "sidewall_images" / "Goodyear" / "SIDE_001 - Viren Viren.JPG"
    raw_front.write_bytes(b"front")
    raw_side.write_bytes(b"side")
    (root / "images" / "front_view").mkdir(parents=True)
    (root / "images" / "side_view").mkdir(parents=True)

    cleaned = clean_and_enrich(normalize_spreadsheet_columns(_sample_raw_frame().iloc[[0]]))
    enriched = attach_and_copy_images(cleaned, paths)

    assert raw_front.exists()
    assert raw_side.exists()
    assert bool(enriched.loc[0, "has_image"]) is True
    assert bool(enriched.loc[0, "has_sidewall_image"]) is True
    assert Path(enriched.loc[0, "dataset_front_path"]).exists()
    assert Path(enriched.loc[0, "dataset_sidewall_path"]).exists()


def test_prepare_dataset_generates_expected_csvs_and_manifest(tmp_path: Path):
    root = _make_dataset_root(tmp_path)
    paths = DatasetPaths(root=root)
    spreadsheet = root / "raw" / "spreadsheet" / "dataset.xlsx"
    _sample_raw_frame().to_excel(spreadsheet, index=False)

    for name in ["IMG_001", "IMG_002", "IMG_003"]:
        (root / "raw" / "tread_images" / f"{name} - Viren Viren.jpg").write_bytes(b"front")
    for name in ["SIDE_001", "SIDE_002", "SIDE_003"]:
        (root / "raw" / "sidewall_images" / "Goodyear" / f"{name} - Viren Viren.JPG").write_bytes(b"side")

    manifest = prepare_dataset(paths=paths, spreadsheet=spreadsheet)

    assert (root / "processed" / "labels.csv").exists()
    assert (root / "processed" / "cleaned_dataset.csv").exists()
    assert (root / "processed" / "features.csv").exists()
    assert (root / "labels" / "tread_depth.csv").exists()
    assert (root / "labels" / "tire_health.csv").exists()
    assert (root / "labels" / "wear_pattern.csv").exists()
    assert (root / "annotations" / "cnn_labels.csv").exists()
    assert (root / "annotations" / "ann_labels.csv").exists()
    assert (root / "annotations" / "ocr_labels.csv").exists()
    assert (root / "metadata" / "dataset_manifest.json").exists()
    assert (root / "splits" / "train" / "labels.csv").exists()
    assert (root / "multi_view" / "train" / "labels.csv").exists()

    features = pd.read_csv(root / "processed" / "features.csv")
    expected_columns = {
        "image_id",
        "tread_1",
        "tread_2",
        "tread_3",
        "tread_4",
        "tread_average",
        "condition",
        "health_score",
        "remaining_life_km",
        "risk_level",
        "front_image_path",
        "sidewall_image_path",
    }
    assert expected_columns.issubset(set(features.columns))
    assert manifest["image_matching"]["front_matched"] == 3
    assert manifest["image_matching"]["sidewall_matched"] == 3

    saved_manifest = json.loads((root / "metadata" / "dataset_manifest.json").read_text())
    assert saved_manifest["row_counts"]["processed_rows"] == 3


def test_prepare_dataset_merges_learning_samples(tmp_path: Path):
    root = _make_dataset_root(tmp_path)
    paths = DatasetPaths(root=root)
    spreadsheet = root / "raw" / "spreadsheet" / "dataset.xlsx"
    _sample_raw_frame().to_excel(spreadsheet, index=False)

    for name in ["IMG_001", "IMG_002", "IMG_003"]:
        (root / "raw" / "tread_images" / f"{name} - Viren Viren.jpg").write_bytes(b"front")

    learning_dir = root / "raw" / "learning_samples"
    (learning_dir / "front_view").mkdir(parents=True)
    (learning_dir / "front_view" / "learn_front_001.jpg").write_bytes(b"learn-front")
    pd.DataFrame(
        [
            {
                "image_path": "learn_front_001.jpg",
                "tread_1": 5.2,
                "tread_2": 5.1,
                "tread_3": 5.0,
                "tread_4": 5.1,
                "brand": "MRF",
                "tire_size": "165/80 R14",
            }
        ]
    ).to_csv(learning_dir / "labels.csv", index=False)

    manifest = prepare_dataset(paths=paths, spreadsheet=spreadsheet)
    features = pd.read_csv(root / "processed" / "features.csv")

    assert manifest["row_counts"]["processed_rows"] == 4
    assert manifest["image_matching"]["front_matched"] == 4
    assert "learn_front_001.jpg" in set(features["image_id"])
    assert str(learning_dir / "labels.csv") in manifest["learning_labels"]


def test_prepare_dataset_merges_app_continuous_learning_samples(tmp_path: Path):
    root = _make_dataset_root(tmp_path)
    paths = DatasetPaths(root=root)
    spreadsheet = root / "raw" / "spreadsheet" / "dataset.xlsx"
    _sample_raw_frame().to_excel(spreadsheet, index=False)

    continuous_dir = root / "continuous_learning"
    (continuous_dir / "front_view").mkdir(parents=True)
    (continuous_dir / "front_view" / "app_sample.jpg").write_bytes(b"app-front")
    pd.DataFrame(
        [
            {
                "session_id": "app-session-1",
                "image_path": "dataset/continuous_learning/front_view/app_sample.jpg",
                "tread_1": 4.8,
                "tread_2": 4.9,
                "tread_3": 5.0,
                "tread_4": 5.1,
                "tread_average": 4.95,
                "wear_pattern": "even",
                "feedback_type": "wrong",
            }
        ]
    ).to_csv(continuous_dir / "labels.csv", index=False)

    manifest = prepare_dataset(paths=paths, spreadsheet=spreadsheet)
    features = pd.read_csv(root / "processed" / "features.csv")

    assert manifest["row_counts"]["processed_rows"] == 4
    assert manifest["image_matching"]["front_matched"] == 1
    assert "dataset/continuous_learning/front_view/app_sample.jpg" in set(features["image_id"])
    assert str(continuous_dir / "labels.csv") in manifest["learning_labels"]


def test_prepare_dataset_allows_unmatched_images(tmp_path: Path):
    root = _make_dataset_root(tmp_path)
    paths = DatasetPaths(root=root)
    spreadsheet = root / "raw" / "spreadsheet" / "dataset.xlsx"
    _sample_raw_frame().to_excel(spreadsheet, index=False)

    manifest = prepare_dataset(paths=paths, spreadsheet=spreadsheet)

    assert manifest["image_matching"]["front_matched"] == 0
    assert manifest["image_matching"]["front_unmatched"] == 3
    assert (root / "multi_view" / "train" / "labels.csv").exists()
    features = pd.read_csv(root / "processed" / "features.csv")
    assert "image_path" in features.columns
