import numpy as np
from ai_model.evaluation.metrics import compute_all_metrics
from ai_model.classes import TreadDepthClass


def _make_tread_array_from_mm(mm_list):
    # produce shape (N,4) normalized arrays where each row repeats the same mm
    arr = np.array([[m, m, m, m] for m in mm_list], dtype=np.float64)
    return arr / 12.0


def test_tread_class_accuracy_perfect():
    # Four samples: new, good, replace_soon, dangerous
    mm_true = [9.0, 7.0, 3.0, 1.0]
    y_true = {"tread_depths": _make_tread_array_from_mm(mm_true)}
    # predictions identical → accuracy 1.0
    y_pred = {"tread_depths": _make_tread_array_from_mm(mm_true)}

    metrics = compute_all_metrics(y_true, y_pred)
    assert metrics["tread_class_accuracy"] == 1.0
    # Check per-class entries exist (may be None for classes without samples)
    for c in TreadDepthClass:
        key = f"tread_{c.value}_accuracy"
        assert key in metrics


def test_tread_class_accuracy_partial():
    mm_true = [9.0, 7.0, 3.0, 1.0]
    mm_pred = [9.0, 6.5, 3.0, 4.5]  # last sample predicted as REPLACE_SOON instead of DANGEROUS
    y_true = {"tread_depths": _make_tread_array_from_mm(mm_true)}
    y_pred = {"tread_depths": _make_tread_array_from_mm(mm_pred)}

    metrics = compute_all_metrics(y_true, y_pred)
    # Expect 3/4 correct
    assert metrics["tread_class_accuracy"] == 0.75
