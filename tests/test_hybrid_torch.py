from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_hybrid_dataset_reads_existing_split():
    from ai_model.hybrid_torch.constants import WEAR_LABELS
    from ai_model.hybrid_torch.dataset import HybridTireDataset

    dataset = HybridTireDataset(PROJECT_ROOT / "dataset" / "splits" / "train")
    inputs, targets = dataset[0]

    assert inputs["image"].shape == (3, 224, 224)
    assert inputs["tread_sequence"].shape == (4, 7)
    assert targets["tread_depths"].shape == (4,)
    assert 0 <= int(targets["wear_pattern"]) < len(WEAR_LABELS)
    assert 0 <= int(targets["condition"]) < 3


def test_hybrid_train_sequence_uses_runtime_visual_proxy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from PIL import Image

    import ai_model.hybrid_torch.dataset as dataset_module
    from ai_model.hybrid_torch.dataset import HybridTireDataset

    split_dir = tmp_path / "splits" / "train"
    split_dir.mkdir(parents=True)
    image_path = tmp_path / "tread.jpg"
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(image_path)
    (split_dir / "labels.csv").write_text(
        "image_path,tread_1,tread_2,tread_3,tread_4,wear_pattern,condition_id\n"
        f"{image_path},2.0,4.0,6.0,8.0,uniform_wear,0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dataset_module,
        "estimate_visual_tread_depths",
        lambda image_bgr: [3.8, 4.0, 4.2, 4.4],
    )

    dataset = HybridTireDataset(split_dir)
    with Image.open(image_path) as image:
        sequence_depths = dataset._sequence_depths(
            str(image_path),
            image,
            np.asarray([2.0, 4.0, 6.0, 8.0], dtype=np.float32),
        )

    assert np.allclose(sequence_depths, np.asarray([3.8, 4.0, 4.2, 4.4], dtype=np.float32))


def test_hybrid_tread_loss_uses_one_mm_hinge_penalty():
    from ai_model.hybrid_torch.constants import TREAD_MAX_MM, WEAR_LABELS
    from ai_model.hybrid_torch.trainer import _loss

    outputs = {
        "tread_depths": torch.tensor([[0.5, 1.0, 1.5, 3.0]], dtype=torch.float32) / TREAD_MAX_MM,
        "health_score": torch.tensor([[0.2]], dtype=torch.float32),
        "remaining_life": torch.tensor([[0.4]], dtype=torch.float32),
        "wear_pattern": torch.zeros((1, len(WEAR_LABELS)), dtype=torch.float32),
        "condition": torch.zeros((1, 3), dtype=torch.float32),
    }
    targets = {
        "tread_depths": torch.zeros((1, 4), dtype=torch.float32),
        "health_score": torch.tensor([[0.1]], dtype=torch.float32),
        "remaining_life": torch.tensor([[0.2]], dtype=torch.float32),
        "wear_pattern": torch.tensor([0], dtype=torch.long),
        "condition": torch.tensor([0], dtype=torch.long),
    }

    error_mm = torch.tensor([[0.5, 1.0, 1.5, 3.0]], dtype=torch.float32)
    base_l1 = torch.nn.functional.smooth_l1_loss(
        outputs["tread_depths"] * TREAD_MAX_MM,
        targets["tread_depths"] * TREAD_MAX_MM,
        beta=0.5,
        reduction="none",
    )
    tread_error = base_l1 + 2.0 * torch.relu(error_mm - 1.0)
    expected = (
        tread_error.mean() * 3.5
        + torch.nn.functional.mse_loss(outputs["health_score"], targets["health_score"]) * 0.7
        + torch.nn.functional.mse_loss(outputs["remaining_life"], targets["remaining_life"]) * 0.7
        + torch.nn.functional.cross_entropy(outputs["wear_pattern"], targets["wear_pattern"]) * 0.5
        + torch.nn.functional.cross_entropy(outputs["condition"], targets["condition"]) * 0.4
    )

    assert torch.isclose(_loss(outputs, targets), expected)


@pytest.mark.slow
def test_hybrid_model_forward_shapes():
    pytest.importorskip("timm")

    from ai_model.hybrid_torch.model import HybridTireModel

    model = HybridTireModel(pretrained=False)
    model.eval()
    with torch.no_grad():
        outputs = model(
            {
                "image": torch.randn(1, 3, 224, 224),
                "tread_sequence": torch.randn(1, 4, 7),
            }
        )

    assert outputs["tread_depths"].shape == (1, 4)
    assert outputs["health_score"].shape == (1, 1)
    assert outputs["remaining_life"].shape == (1, 1)
    assert outputs["wear_pattern"].shape == (1, 6)
    assert outputs["condition"].shape == (1, 3)


def test_archive_legacy_artifacts_moves_existing_files(tmp_path: Path):
    from ai_model.hybrid_torch.trainer import archive_legacy_artifacts

    project = tmp_path / "project"
    saved = project / "ai_model" / "saved_models"
    saved.mkdir(parents=True)
    (saved / "old.pt").write_text("weights", encoding="utf-8")
    (saved / "old_dir").mkdir()
    (saved / "old_dir" / "metrics.json").write_text("{}", encoding="utf-8")

    archive = archive_legacy_artifacts(saved, project_root=project)

    assert archive is not None
    assert not (saved / "old.pt").exists()
    assert (archive / "old.pt").exists()
    assert (archive / "old_dir" / "metrics.json").exists()


def test_backend_health_reports_hybrid_model_version():
    import sys
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from app.routes.health import router
    from ai_model.hybrid_torch.constants import HYBRID_MODEL_VERSION

    class FakeInference:
        _model_version = HYBRID_MODEL_VERSION
        _model_source = "pytorch_hybrid"
        _model_checkpoint = "ai_model/saved_models/hybrid_torch/model_best.pt"
        _load_error = None

        def is_ready(self) -> bool:
            return True

    app = FastAPI()
    app.include_router(router, prefix="/health")
    app.state.inference_service = FakeInference()

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    components = response.json()["components"]
    assert components["model_version"] == HYBRID_MODEL_VERSION
    assert components["model_source"] == "pytorch_hybrid"
    assert components["model_checkpoint"].endswith("model_best.pt")
