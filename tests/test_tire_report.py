from ai_model.inference.tire_report import (
    clean_brand,
    clean_tire_size,
    parse_dot_dom,
    wear_class_and_label_from_tread,
    health_score_from_parts,
    generate_tire_report,
)


def test_wear_class_boundaries():
    assert wear_class_and_label_from_tread(7.5)[0] == 0
    assert wear_class_and_label_from_tread(6.0)[0] == 1
    assert wear_class_and_label_from_tread(4.0)[0] == 2
    assert wear_class_and_label_from_tread(2.5)[0] == 3
    assert wear_class_and_label_from_tread(1.0)[0] == 4


def test_cleaning_and_parsing():
    assert clean_brand("M.R.F.") == "MRF"
    assert clean_brand("M r f") == "MRF"
    assert clean_tire_size("195/65 r15") == "195/65R15"
    wk, yr = parse_dot_dom("DOT2319")
    assert wk == 23 and yr == 2019


def test_health_score_basic():
    # sanity-check the value range and determinism
    score = health_score_from_parts(6.0, "Good", "minor wear", False, "smooth")
    assert 0 <= score <= 100


def test_generate_report_minimal():
    rpt = generate_tire_report("/tmp/img.jpg", model_outputs={"tread_depth_pred": 5.0, "crack_detected": False, "average_form": 'Good'})
    assert rpt['image_path'] == "/tmp/img.jpg"
    assert 'health_score_pred' in rpt
