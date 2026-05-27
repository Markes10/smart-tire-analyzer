from dataset.class_schemas import get_classes, mm_to_tread_depth_class, confidence_pct_to_label
import pytest


def test_get_classes_wear_pattern():
    expected = [
        "Even Wear",
        "Center Wear",
        "Edge Wear",
        "One Side Wear",
        "Cupping Wear",
        "Feathering Wear",
        "Patch Wear",
    ]
    assert get_classes("wear_pattern") == expected


@pytest.mark.parametrize(
    "mm,expected",
    [
        (9.5, "New"),
        (8.0, "Good"),
        (6.5, "Good"),
        (5.0, "Moderate"),
        (3.0, "Replace Soon"),
        (1.5, "Dangerous"),
        (0.5, "Dangerous"),
    ],
)
def test_mm_to_tread_depth_class_boundaries(mm, expected):
    assert mm_to_tread_depth_class(mm) == expected


def test_confidence_mapping():
    assert confidence_pct_to_label(95) == "High Confidence"
    assert confidence_pct_to_label(85) == "Medium Confidence"
    assert confidence_pct_to_label(50) == "Low Confidence"
