"""Safe catalog for legacy model, pipeline, and orchestration modules.

The old TensorFlow/Airflow/Kubeflow pieces are useful project assets, but they
must stay lazy so the normal FastAPI runtime can start without optional ML
platform packages installed.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[3]


LEGACY_ARCHITECTURES: tuple[dict[str, Any], ...] = (
    {
        "id": "cnn_lite_extractor",
        "name": "Lite CNN feature extractor",
        "module": "ai_model.cnn.mobilenetv2_extractor",
        "file": "ai_model/cnn/mobilenetv2_extractor.py",
        "optional_dependency": "keras",
        "smoke_safe": True,
        "purpose": "Offline-safe spatial tire feature extractor.",
    },
    {
        "id": "cnn_feature_map",
        "name": "Multi-scale CNN feature map builder",
        "module": "ai_model.cnn.feature_map",
        "file": "ai_model/cnn/feature_map.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Legacy multi-scale visual feature aggregation.",
    },
    {
        "id": "ann_fusion_layer",
        "name": "ANN multimodal fusion layer",
        "module": "ai_model.ann.fusion_layer",
        "file": "ai_model/ann/fusion_layer.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Gated/concat fusion for CNN, ViT, RNN, and context vectors.",
    },
    {
        "id": "ann_prediction_head",
        "name": "ANN prediction head",
        "module": "ai_model.ann.prediction_head",
        "file": "ai_model/ann/prediction_head.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Legacy multi-head tread, health, life, and wear prediction.",
    },
    {
        "id": "rnn_lstm_tread",
        "name": "LSTM tread sequence model",
        "module": "ai_model.rnn.lstm_tread",
        "file": "ai_model/rnn/lstm_tread.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Temporal sequence encoder for tread readings.",
    },
    {
        "id": "rnn_temporal_features",
        "name": "Temporal wear feature helpers",
        "module": "ai_model.rnn.temporal_features",
        "file": "ai_model/rnn/temporal_features.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Depth-derived wear classification, confidence, and velocity.",
    },
    {
        "id": "vit_encoder",
        "name": "Vision Transformer encoder",
        "module": "ai_model.transformer.vit_encoder",
        "file": "ai_model/transformer/vit_encoder.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": True,
        "purpose": "Legacy patch-based visual context encoder.",
    },
    {
        "id": "gemini_prompt_builder",
        "name": "Gemini prompt builder",
        "module": "api_integrations.gemini.prompt_builder",
        "file": "api_integrations/gemini/prompt_builder.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Structured tire-safety prompting reused by GeminiService.",
    },
    {
        "id": "maps_terrain_analyzer",
        "name": "Terrain analyzer",
        "module": "api_integrations.google_maps.terrain_analyzer",
        "file": "api_integrations/google_maps/terrain_analyzer.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Legacy terrain wear multipliers reused by MapsService.",
    },
    {
        "id": "maps_traffic_fetcher",
        "name": "Traffic fetcher",
        "module": "api_integrations.google_maps.traffic_fetcher",
        "file": "api_integrations/google_maps/traffic_fetcher.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Time-based traffic density and tire-wear multipliers.",
    },
    {
        "id": "feedback_service",
        "name": "Legacy feedback service",
        "module": "continuous_learning.feedback_service",
        "file": "continuous_learning/feedback_service.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Wrong-prediction audit and feedback statistics.",
    },
    {
        "id": "version_manager",
        "name": "Model version manager",
        "module": "continuous_learning.model_versions.version_manager",
        "file": "continuous_learning/model_versions/version_manager.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Legacy semantic model registry and rollback metadata.",
    },
    {
        "id": "validation_check",
        "name": "Promotion validation gate",
        "module": "continuous_learning.retraining.validation_check",
        "file": "continuous_learning/retraining/validation_check.py",
        "optional_dependency": "tensorflow",
        "smoke_safe": False,
        "purpose": "Legacy validation gate reused by quarantined promotion.",
    },
    {
        "id": "clean_dataset",
        "name": "Dataset cleaning helpers",
        "module": "dataset.preprocessing.clean_dataset",
        "file": "dataset/preprocessing/clean_dataset.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Legacy data repair helpers reused by prepare_dataset.",
    },
    {
        "id": "split_dataset",
        "name": "Dataset split helpers",
        "module": "dataset.preprocessing.split_dataset",
        "file": "dataset/preprocessing/split_dataset.py",
        "optional_dependency": None,
        "smoke_safe": False,
        "purpose": "Legacy stratified splitting reused when data supports it.",
    },
)


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _file_exists(relative_path: str) -> bool:
    return (PROJECT_ROOT / relative_path).exists()


def _shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _shape(item) for key, item in value.items()}
    return str(value)


def _model_summary(model: Any) -> dict[str, Any]:
    count_params = getattr(model, "count_params", None)
    return {
        "built": True,
        "name": str(getattr(model, "name", "legacy_model")),
        "output_shape": _shape(getattr(model, "output_shape", None)),
        "parameters": int(count_params()) if callable(count_params) else None,
    }


def _smoke_builders() -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        "cnn_lite_extractor": lambda: _model_summary(
            importlib.import_module("ai_model.cnn.mobilenetv2_extractor").build_lite_cnn_extractor(
                input_shape=(32, 32, 4)
            )
        ),
        "cnn_feature_map": lambda: {
            "built": True,
            "name": importlib.import_module("ai_model.cnn.feature_map").MultiScaleFeatureBuilder(
                output_dim=16
            ).name,
        },
        "ann_fusion_layer": lambda: _model_summary(
            importlib.import_module("ai_model.ann.fusion_layer").build_fusion_model(
                cnn_dim=8,
                vit_dim=8,
                rnn_dim=8,
                context_dim=4,
                output_dim=16,
                fusion_type="concat",
            )
        ),
        "ann_prediction_head": lambda: _model_summary(
            importlib.import_module("ai_model.ann.prediction_head").build_prediction_head(
                fused_dim=16
            )
        ),
        "rnn_lstm_tread": lambda: _model_summary(
            importlib.import_module("ai_model.rnn.lstm_tread").build_lstm_tread_model(
                input_dim=4,
                hidden_units=8,
                num_layers=1,
                output_dim=16,
            )
        ),
        "rnn_temporal_features": lambda: _model_summary(
            importlib.import_module("ai_model.rnn.temporal_features").build_temporal_feature_extractor(
                sequence_dim=4,
                hidden_dim=8,
                output_dim=16,
            )
        ),
        "vit_encoder": lambda: _model_summary(
            importlib.import_module("ai_model.transformer.vit_encoder").build_vit_encoder(
                input_shape=(32, 32, 4),
                patch_size=16,
                embedding_dim=32,
                num_heads=4,
                num_transformer_blocks=1,
                output_dim=32,
            )
        ),
    }


def get_legacy_architecture_catalog(include_smoke: bool = False) -> list[dict[str, Any]]:
    """Return lazy registration metadata for legacy modules."""
    builders = _smoke_builders() if include_smoke else {}
    catalog: list[dict[str, Any]] = []
    for entry in LEGACY_ARCHITECTURES:
        dependency = entry.get("optional_dependency")
        module_ready = _module_available(str(entry["module"]))
        dependency_ready = True if not dependency else _module_available(str(dependency))
        status = "registered" if module_ready and dependency_ready else "optional_dependency_missing"
        if not module_ready:
            status = "module_missing"
        smoke: dict[str, Any] = {"status": "not_run"}
        builder = builders.get(str(entry["id"]))
        if builder:
            try:
                smoke = {"status": "passed", **builder()}
            except Exception as exc:
                smoke = {"status": "skipped", "reason": str(exc)}
        catalog.append(
            {
                **entry,
                "module_available": module_ready,
                "file_present": _file_exists(str(entry["file"])),
                "dependency_available": dependency_ready,
                "status": status,
                "smoke": smoke,
            }
        )
    return catalog


def get_orchestrator_status() -> dict[str, Any]:
    """Report optional Airflow/Kubeflow adapter readiness without importing them."""
    airflow_file = PROJECT_ROOT / "mlops" / "airflow_smart_tire_dag.py"
    kubeflow_file = PROJECT_ROOT / "mlops" / "kubeflow_pipeline.py"
    adapters = {
        "airflow": {
            "adapter": str(airflow_file),
            "adapter_present": airflow_file.exists(),
            "dependency_available": _module_available("airflow"),
        },
        "kubeflow": {
            "adapter": str(kubeflow_file),
            "adapter_present": kubeflow_file.exists(),
            "dependency_available": _module_available("kfp"),
        },
    }
    for adapter in adapters.values():
        adapter["status"] = (
            "ready"
            if adapter["adapter_present"] and adapter["dependency_available"]
            else "optional_dependency_missing"
            if adapter["adapter_present"]
            else "adapter_missing"
        )
    return adapters


def get_legacy_class_summary() -> dict[str, Any]:
    """Expose class constants from the legacy unified class module."""
    try:
        from ai_model.classes import CLASS_SUMMARY, NUM_WEAR_CLASSES

        return {
            "num_wear_classes": int(NUM_WEAR_CLASSES),
            "class_summary": dict(CLASS_SUMMARY),
            "status": "available",
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def get_legacy_versions_snapshot() -> dict[str, Any]:
    """Expose semantic version-manager data without making it authoritative."""
    try:
        from continuous_learning.model_versions.version_manager import load_registry, list_versions

        registry = load_registry()
        versions = list_versions()
        return {
            "status": "available",
            "current_version": registry.get("current_version"),
            "latest": registry.get("latest"),
            "versions": versions,
            "version_count": len(versions),
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc), "versions": [], "version_count": 0}


def get_legacy_diagnostics(include_smoke: bool = False) -> dict[str, Any]:
    """Aggregate legacy diagnostics for registry and enterprise dashboard views."""
    return {
        "legacy_architectures": get_legacy_architecture_catalog(include_smoke=include_smoke),
        "legacy_versions": get_legacy_versions_snapshot(),
        "orchestrators": get_orchestrator_status(),
        "class_summary": get_legacy_class_summary(),
    }
