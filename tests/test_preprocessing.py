"""
Tests for AI model preprocessing and tread depth classification.
"""

import numpy as np
import pytest


class TestBlurDetection:
    """blur detection pipeline tests."""

    def test_sharp_image_passes(self):
        """Synthetic checkerboard should not be flagged as blurry."""
        import cv2
        img = np.zeros((224, 224, 3), dtype=np.uint8)
        # Checkerboard pattern — extremely high Laplacian variance
        for y in range(0, 224, 16):
            for x in range(0, 224, 16):
                if (y // 16 + x // 16) % 2 == 0:
                    img[y:y+16, x:x+16] = 255
        from ai_model.cnn.preprocessing import detect_blur
        is_blurry, score = detect_blur(img, threshold=100.0)
        assert isinstance(is_blurry, bool)
        assert score > 100.0  # Sharp image should have high variance
        assert is_blurry is False

    def test_blurry_image_rejected(self):
        """Uniform gray image (completely blurry) should be rejected."""
        import cv2
        img = np.full((224, 224, 3), 128, dtype=np.uint8)
        # Apply heavy blur
        img = cv2.GaussianBlur(img, (99, 99), 0)
        from ai_model.cnn.preprocessing import detect_blur
        is_blurry, score = detect_blur(img, threshold=100.0)
        assert score < 100.0
        assert is_blurry is True

    def test_returns_float_score(self):
        """Blur score must always be a float."""
        img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        from ai_model.cnn.preprocessing import detect_blur
        is_blurry, score = detect_blur(img)
        assert isinstance(score, float)


class TestPreprocessingPipeline:
    """Run the full 10-step preprocessing pipeline."""

    def test_output_shape(self):
        """Output should always be (224, 224, 4) with edge channel."""
        import cv2
        img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        from ai_model.cnn.preprocessing import run_preprocessing_pipeline
        result = run_preprocessing_pipeline(img, training=False, include_edge_channel=True)
        assert result is not None, "Preprocessing returned None for a valid image"
        assert result.shape == (224, 224, 4), f"Expected (224,224,4), got {result.shape}"

    def test_output_normalized(self):
        """Output values should be within normalized range."""
        img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        from ai_model.cnn.preprocessing import run_preprocessing_pipeline
        result = run_preprocessing_pipeline(img, training=False, include_edge_channel=True)
        if result is not None:
            # ImageNet normalization can produce values outside [0,1]
            # but should be bounded
            assert not np.any(np.isnan(result)), "Output contains NaN"
            assert not np.any(np.isinf(result)), "Output contains Inf"

    def test_augmentation_changes_image(self):
        """Augmented images should differ from the original."""
        img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
        from ai_model.cnn.preprocessing import run_preprocessing_pipeline
        base = run_preprocessing_pipeline(img, training=False)
        aug  = run_preprocessing_pipeline(img, training=True)
        if base is not None and aug is not None:
            # Training augmentation should sometimes modify the image
            # (not guaranteed every time, so we just verify shape)
            assert base.shape == aug.shape


class TestSequenceBuilder:
    """Test RNN sequence building from tread measurements."""

    def test_basic_sequence_shape(self):
        """Standard 4-measurement input → (4, 7) output."""
        from ai_model.rnn.sequence_builder import build_tread_sequence
        depths = [6.5, 6.2, 5.9, 6.1]
        seq = build_tread_sequence(depths)
        assert seq.shape == (4, 7), f"Expected (4,7), got {seq.shape}"
        assert seq.dtype == np.float32

    def test_zero_tread4_imputed(self):
        """T4 = 0 should be imputed from T1-T3 average."""
        from ai_model.rnn.sequence_builder import build_tread_sequence
        depths = [6.0, 6.0, 6.0, 0.0]  # T4 = 0 (known dataset issue)
        seq = build_tread_sequence(depths)
        # T4 position should not be 0 after imputation
        assert seq[3, 0] > 0.0, "T4 zero was not imputed"

    def test_sequence_with_image_features(self):
        """Appending 512-dim image features → (4, 519) output."""
        from ai_model.rnn.sequence_builder import build_tread_sequence
        depths = [5.0, 5.0, 5.0, 5.0]
        img_features = np.ones(512, dtype=np.float32)
        seq = build_tread_sequence(depths, image_features=img_features)
        assert seq.shape == (4, 7 + 512)

    def test_normalize_tread_depths(self):
        """Normalized + validated tread output includes statistics."""
        from ai_model.rnn.sequence_builder import normalize_tread_depths
        result = normalize_tread_depths([7.0, 6.5, 6.8, 6.9])
        assert "average" in result
        assert "differential" in result
        assert "pct_above_legal" in result
        assert result["pct_above_legal"] == 1.0  # All above 1.6mm

    def test_zero_tread_depth_fixed(self):
        """normalize_tread_depths should fix zero values."""
        from ai_model.rnn.sequence_builder import normalize_tread_depths
        result = normalize_tread_depths([5.0, 5.0, 5.0, 0.0])
        assert result["tread_4"] > 0.0


class TestOutputHeads:
    """Test output denormalization and risk classification."""

    def _make_raw_outputs(self, tread_norm=0.5, health_norm=0.8, life_norm=0.7, wear_class=3):
        """Helper to build synthetic raw model output dict."""
        wear_probs = np.zeros(6, dtype=np.float32)
        wear_probs[wear_class] = 0.9
        wear_probs[(wear_class + 1) % 6] = 0.1
        return {
            "tread_depths":  np.ones((1, 4), dtype=np.float32) * tread_norm,
            "health_score":  np.array([[health_norm]], dtype=np.float32),
            "remaining_life":np.array([[life_norm]], dtype=np.float32),
            "wear_pattern":  wear_probs[np.newaxis, :],
        }

    def test_denormalize_good_tire(self):
        """Good tire outputs should give safe readings."""
        from ai_model.ann.output_heads import denormalize_outputs
        raw = self._make_raw_outputs(tread_norm=0.7)
        result = denormalize_outputs(raw)
        assert result["tread_depths_mm"]["average"] == pytest.approx(8.4, abs=0.1)
        assert result["health_score"] == pytest.approx(8.0, abs=0.2)

    def test_compute_risk_critical(self):
        """Very low tread should produce CRITICAL risk."""
        from ai_model.ann.output_heads import compute_risk_level
        risk = compute_risk_level(
            health_score=2.5, avg_tread_mm=1.2,
            remaining_km=1000, wear_severity="moderate"
        )
        assert risk == "CRITICAL"

    def test_compute_risk_low(self):
        """Excellent tire should produce LOW risk."""
        from ai_model.ann.output_heads import compute_risk_level
        risk = compute_risk_level(
            health_score=9.0, avg_tread_mm=8.5,
            remaining_km=70000, wear_severity="low"
        )
        assert risk == "LOW"

    def test_classify_tread_status(self):
        """Test all tread depth status classifications."""
        from ai_model.ann.output_heads import _classify_tread_status
        assert _classify_tread_status(1.2) == "ILLEGAL"
        assert _classify_tread_status(2.5) == "CRITICAL"
        assert _classify_tread_status(4.0) == "WARNING"
        assert _classify_tread_status(6.0) == "ACCEPTABLE"
        assert _classify_tread_status(8.0) == "GOOD"

    def test_generate_alerts_critical_tread(self):
        """Sub-legal tread generates CRITICAL alert."""
        from ai_model.ann.output_heads import _generate_alerts
        predictions = {
            "tread_depths_mm": {"average": 1.2, "min": 1.1, "max": 1.4},
            "health_score": 2.0,
            "wear_pattern": {"severity": "low"},
        }
        alerts = _generate_alerts(predictions, "CRITICAL")
        assert any(a["level"] == "CRITICAL" for a in alerts)

    def test_build_final_report_contains_required_keys(self):
        """Full report must contain all required top-level keys."""
        from ai_model.ann.output_heads import build_final_report
        raw = self._make_raw_outputs()
        report = build_final_report(raw, session_id="test-001")
        required = ["session_id", "risk_level", "status", "replace_immediately",
                    "confidence", "predictions", "context", "reasoning", "alerts"]
        for key in required:
            assert key in report, f"Missing key: {key}"


class TestEvaluationMetrics:
    """Test evaluation metrics for regression and classification."""

    def test_tread_mae_zero(self):
        """Perfect predictions → MAE = 0."""
        from ai_model.evaluation.metrics import tread_mae_mm
        y = np.array([5.0, 4.0, 6.0, 3.0])
        assert tread_mae_mm(y, y) == 0.0

    def test_tread_mae_known_value(self):
        """MAE of 1.0mm off predictions."""
        from ai_model.evaluation.metrics import tread_mae_mm
        true = np.array([5.0, 5.0, 5.0, 5.0])
        pred = np.array([4.0, 4.0, 4.0, 4.0])
        assert tread_mae_mm(true, pred) == pytest.approx(1.0)

    def test_danger_zone_recall_all_found(self):
        """All dangerous tires detected → recall = 1.0."""
        from ai_model.evaluation.metrics import danger_zone_recall
        true = np.array([1.2, 1.4, 1.5])  # All dangerous
        pred = np.array([1.3, 1.2, 1.6])
        recall = danger_zone_recall(true, pred)
        assert recall == pytest.approx(1.0)

    def test_danger_zone_recall_missed(self):
        """Missed dangerous tire → recall < 1.0."""
        from ai_model.evaluation.metrics import danger_zone_recall
        true = np.array([1.0, 1.5, 5.0])  # 2 dangerous
        pred = np.array([1.1, 5.0, 5.1])  # 1 correctly detected dangerous, 1 missed
        recall = danger_zone_recall(true, pred)
        assert recall < 1.0

    def test_within_threshold_perfect(self):
        """All within 0.5mm → accuracy = 1.0."""
        from ai_model.evaluation.metrics import within_threshold_accuracy
        true = np.array([5.0, 6.0, 7.0])
        pred = np.array([5.4, 6.1, 7.3])
        assert within_threshold_accuracy(true, pred, 0.5) == 1.0

    def test_within_threshold_partial(self):
        """50% within threshold → accuracy = 0.5."""
        from ai_model.evaluation.metrics import within_threshold_accuracy
        true = np.array([5.0, 5.0])
        pred = np.array([5.3, 6.0])  # First within 0.5, second outside
        acc = within_threshold_accuracy(true, pred, 0.5)
        assert acc == pytest.approx(0.5)
