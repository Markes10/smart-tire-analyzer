"""
Optional Kubeflow pipeline skeleton.

The local project does not require Kubeflow. This file documents the cloud
pipeline shape for demos and future deployment.
"""

from __future__ import annotations

try:
    from kfp import dsl
except Exception:  # pragma: no cover - optional platform dependency
    dsl = None


if dsl is not None:

    @dsl.component
    def prepare_dataset() -> str:
        return "dataset/splits"

    @dsl.component
    def train_model(dataset_path: str) -> str:
        return "ai_model/saved_models/hybrid_torch/model_best.pt"

    @dsl.component
    def register_model(model_path: str) -> str:
        return "ai_model/saved_models/model_registry.json"

    @dsl.pipeline(name="smart-tire-mlops-pipeline")
    def smart_tire_pipeline():
        dataset_task = prepare_dataset()
        model_task = train_model(dataset_path=dataset_task.output)
        register_model(model_path=model_task.output)
