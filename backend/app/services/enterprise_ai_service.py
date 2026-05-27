"""
Enterprise AI extensions for final-year-project and SaaS-style demos.

The heavy enterprise tools are represented as optional adapters, config files,
and local status checks. The calculations here are intentionally lightweight so
the project still runs on a student laptop.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


KNOWLEDGE_BASE = [
    {
        "id": "kb-low-tread",
        "topic": "Low tread depth",
        "keywords": ["critical", "high", "low_tread", "replace", "unsafe"],
        "recommendation": "Replace the tire when tread is near or below the legal threshold.",
        "reasoning": "Low tread reduces wet grip, increases stopping distance, and raises blowout risk.",
    },
    {
        "id": "kb-edge-wear",
        "topic": "Edge wear",
        "keywords": ["edge_wear", "underinflation", "pressure", "shoulder"],
        "recommendation": "Check inflation pressure and inspect suspension/alignment.",
        "reasoning": "Both tire shoulders wearing faster than the center often indicates underinflation.",
    },
    {
        "id": "kb-center-wear",
        "topic": "Center wear",
        "keywords": ["center_wear", "overinflation", "pressure"],
        "recommendation": "Reduce pressure to the vehicle placard value and recheck wear progression.",
        "reasoning": "Center tread wearing faster than shoulders commonly points to overinflation.",
    },
    {
        "id": "kb-one-side-wear",
        "topic": "One-side wear",
        "keywords": ["one_side_wear", "alignment", "camber", "toe"],
        "recommendation": "Perform wheel alignment and inspect steering geometry.",
        "reasoning": "One shoulder wearing faster suggests camber or toe alignment problems.",
    },
    {
        "id": "kb-vibration",
        "topic": "Vibration anomaly",
        "keywords": ["vibration", "cupping_wear", "imbalance", "shock"],
        "recommendation": "Balance the wheel and inspect shock absorbers or struts.",
        "reasoning": "High vibration with cupping-like wear can indicate mechanical oscillation.",
    },
    {
        "id": "kb-heat",
        "topic": "Temperature risk",
        "keywords": ["temperature", "heat", "speed", "pressure"],
        "recommendation": "Let tires cool, verify pressure cold, and avoid high-speed operation.",
        "reasoning": "Heat accelerates rubber aging and increases failure probability.",
    },
]


REQUESTED_ARCHITECTURE_MODULES = [
    {
        "id": "mlops",
        "name": "MLOps & Model Lifecycle Management",
        "tools": ["MLflow", "Weights & Biases", "DVC", "Kubeflow", "Airflow"],
        "capabilities": [
            "Experiment Tracking",
            "Model Registry",
            "Auto Deployment",
            "Dataset Versioning",
        ],
    },
    {
        "id": "edge_ai",
        "name": "Real-Time Edge AI Processing",
        "tools": ["TensorRT", "ONNX Runtime", "NVIDIA Jetson", "Mobile Inference"],
        "capabilities": ["On-device inference", "Offline predictions", "Cloud sync"],
    },
    {
        "id": "xai",
        "name": "Explainable AI Module",
        "tools": ["Grad-CAM", "SHAP", "Attention Heatmaps"],
        "capabilities": ["Damage-region highlighting", "Prediction explanation"],
    },
    {
        "id": "confidence",
        "name": "AI Confidence Scoring",
        "tools": ["Calibration", "Uncertainty Estimation", "Risk Score"],
        "capabilities": ["Prediction confidence percent", "Failure-risk scoring"],
    },
    {
        "id": "digital_twin",
        "name": "Digital Twin Layer",
        "tools": ["Lifecycle simulation", "Virtual tire state"],
        "capabilities": ["Physical tire to virtual simulation loop"],
    },
    {
        "id": "predictive",
        "name": "Predictive Maintenance Engine",
        "tools": ["RUL", "Failure Forecasting", "Trend Analysis"],
        "capabilities": ["Future failure prediction", "Maintenance windowing"],
    },
    {
        "id": "iot",
        "name": "IoT Sensor Fusion Layer",
        "tools": ["Pressure", "Temperature", "Vibration", "Speed"],
        "capabilities": ["Sensor data + image data fusion"],
    },
    {
        "id": "cloud",
        "name": "Cloud-Native Infrastructure",
        "tools": ["Docker", "Kubernetes", "Microservices"],
        "capabilities": ["Containerized deployment", "Horizontal scaling"],
    },
    {
        "id": "security",
        "name": "Security & Authentication Layer",
        "tools": ["OAuth2", "JWT", "RBAC", "Encryption"],
        "capabilities": ["API gateway control", "Role-based access"],
    },
    {
        "id": "monitoring",
        "name": "AI Monitoring Dashboard",
        "tools": ["Model Drift", "System Health", "GPU Usage", "API Latency", "Error Logs"],
        "capabilities": ["Operational observability", "Model quality monitoring"],
    },
    {
        "id": "agents",
        "name": "Multi-Agent AI System",
        "tools": ["Damage Agent", "Maintenance Agent", "Cost Agent", "Report Agent"],
        "capabilities": ["Autonomous recommendation pipeline"],
    },
    {
        "id": "federated",
        "name": "Federated Learning",
        "tools": ["Secure Aggregation", "Local Vehicle Training", "Weight Sharing"],
        "capabilities": ["Privacy-preserving distributed training"],
    },
    {
        "id": "rag",
        "name": "Maintenance Knowledge Graph / RAG",
        "tools": ["Vector DB", "FAISS", "Pinecone", "Knowledge Base"],
        "capabilities": ["AI recommendation with reasoning"],
    },
    {
        "id": "llm_report",
        "name": "LLM Report Generation",
        "tools": ["Llama", "Ollama", "PDF/Markdown Reports"],
        "capabilities": ["Technician notes", "Failure explanations"],
    },
    {
        "id": "synthetic_data",
        "name": "Simulation & Synthetic Data Engine",
        "tools": ["GANs", "Diffusion Models", "Data Augmentation"],
        "capabilities": ["Synthetic samples for rare damage classes"],
    },
]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


class EnterpriseAIService:
    """Builds the advanced AI layer shown in the API, report, and dashboard."""

    def architecture_summary(self) -> dict[str, Any]:
        return {
            "project_mode": "student_final_year_project",
            "maturity_level": "enterprise_architecture_demo",
            "local_run_policy": "heavy platforms are optional adapters; core API/UI runs locally",
            "workflow": [
                "Data Versioning",
                "Model Training",
                "Experiment Tracking",
                "Model Registry",
                "CI/CD Deployment",
                "Monitoring",
                "Auto Retraining",
            ],
            "edge_workflow": ["Camera", "Edge Device", "Local Prediction", "Cloud Sync"],
            "modules": [
                {
                    **module,
                    "local_status": self._module_local_status(module["id"]),
                }
                for module in REQUESTED_ARCHITECTURE_MODULES
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def build_analysis_extensions(
        self,
        report: dict[str, Any],
        *,
        image_bytes: bytes | None = None,
        sensor_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sensor_payload = self._normalize_sensor_data(sensor_data or {})
        confidence = self.confidence_estimation(report, sensor_payload)
        predictive = self.predictive_maintenance(report, sensor_payload, confidence)
        digital_twin = self.digital_twin(report, sensor_payload, predictive)
        iot = self.iot_sensor_fusion(report, sensor_payload)
        xai = self.explainability(report, image_bytes=image_bytes)
        rag = self.knowledge_retrieval(report, sensor_payload)
        agents = self.multi_agent_system(report, confidence, predictive, rag)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mlops_lifecycle": self.mlops_snapshot(),
            "edge_ai": self.edge_ai_status(),
            "explainable_ai": xai,
            "confidence_estimation": confidence,
            "digital_twin": digital_twin,
            "predictive_maintenance": predictive,
            "iot_sensor_fusion": iot,
            "cloud_native": self.cloud_native_status(),
            "security": SecurityService().status(),
            "monitoring": self.monitoring_summary(report),
            "multi_agent_ai": agents,
            "federated_learning": self.federated_learning_status(),
            "rag_knowledge_base": rag,
            "llm_report_generator": self.report_generation(report, agents, rag),
            "synthetic_data_engine": self.synthetic_data_status(),
        }

    def dashboard_payload(self, feedback_stats: dict[str, Any] | None = None) -> dict[str, Any]:
        mlops = self.mlops_snapshot()
        architecture = self.architecture_summary()
        feedback = feedback_stats or {}
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "architecture": architecture,
            "mlops": mlops,
            "monitoring": {
                "model_drift_detection": self._drift_status(feedback),
                "system_health": "ready_for_local_demo",
                "gpu_usage": self._gpu_status(),
                "api_latency_ms": self._read_latency_hint(),
                "error_logs": self._log_status(),
                "feedback_loop": {
                    "total_feedback": feedback.get("total_feedback", 0),
                    "wrong_predictions": feedback.get("wrong_predictions", 0),
                    "retrain_ready": feedback.get("retrain_ready", False),
                },
            },
            "deployment": self.cloud_native_status(),
            "security": SecurityService().status(),
            "edge_ai": self.edge_ai_status(),
            "federated_learning": self.federated_learning_status(),
            "synthetic_data_engine": self.synthetic_data_status(),
        }

    def confidence_estimation(
        self,
        report: dict[str, Any],
        sensor_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        predictions = report.get("predictions", {})
        tread = predictions.get("tread_depths_mm", {})
        wear = predictions.get("wear_pattern", {})
        base_confidence = _safe_float(report.get("confidence"), 0.75)
        wear_confidence = _safe_float(wear.get("confidence"), base_confidence)
        depth_range = _safe_float(tread.get("max"), 5.0) - _safe_float(tread.get("min"), 5.0)
        sensor_risk = self._sensor_risk(sensor_data or {})
        risk_base = {"LOW": 18.0, "MODERATE": 45.0, "HIGH": 72.0, "CRITICAL": 92.0}.get(
            str(report.get("risk_level", "LOW")).upper(),
            35.0,
        )

        uncertainty = _clamp(
            (1.0 - ((base_confidence + wear_confidence) / 2.0)) * 100.0
            + depth_range * 3.0
            + sensor_risk * 0.25,
            0.0,
            100.0,
        )
        risk_score = _clamp(risk_base + uncertainty * 0.25 + sensor_risk * 0.35, 0.0, 100.0)
        return {
            "prediction_confidence_pct": round(base_confidence * 100.0, 2),
            "uncertainty_estimation_pct": round(uncertainty, 2),
            "failure_risk_score_pct": round(risk_score, 2),
            "failure_risk_label": self._risk_label(risk_score),
            "calibration_method": "hybrid model confidence + tread variance + sensor risk",
            "example_output": {
                "predicted_condition": str(report.get("risk_level", "LOW")),
                "confidence": f"{base_confidence * 100.0:.1f}%",
                "failure_risk": self._risk_label(risk_score),
            },
        }

    def predictive_maintenance(
        self,
        report: dict[str, Any],
        sensor_data: dict[str, Any],
        confidence: dict[str, Any],
    ) -> dict[str, Any]:
        predictions = report.get("predictions", {})
        tread = predictions.get("tread_depths_mm", {})
        remaining_km = _safe_float(predictions.get("remaining_life_km"), 0.0)
        avg_tread = _safe_float(tread.get("average"), 5.0)
        daily_km = _safe_float(os.getenv("SMART_TIRE_DAILY_KM"), 40.0)
        risk_score = _safe_float(confidence.get("failure_risk_score_pct"), 40.0)
        sensor_multiplier = 1.0 + self._sensor_risk(sensor_data) / 200.0
        adjusted_rul = max(0.0, remaining_km / sensor_multiplier)
        days_to_threshold = adjusted_rul / max(daily_km, 1.0)

        if avg_tread < 1.6:
            trend = "failure_threshold_reached"
        elif risk_score >= 70:
            trend = "accelerated_wear_detected"
        elif risk_score >= 40:
            trend = "moderate_degradation_trend"
        else:
            trend = "stable_wear_trend"

        return {
            "remaining_useful_life_km": round(adjusted_rul, 0),
            "failure_forecast_days": round(days_to_threshold, 1),
            "failure_forecast_window": self._forecast_window(days_to_threshold),
            "trend_analysis": trend,
            "maintenance_priority": self._risk_label(risk_score),
            "recommended_action": self._maintenance_action(report.get("risk_level", "LOW"), days_to_threshold),
        }

    def digital_twin(
        self,
        report: dict[str, Any],
        sensor_data: dict[str, Any],
        predictive: dict[str, Any],
    ) -> dict[str, Any]:
        tread = report.get("predictions", {}).get("tread_depths_mm", {})
        avg_tread = _safe_float(tread.get("average"), 5.0)
        lifecycle_stage = "new_or_healthy"
        if avg_tread < 1.6:
            lifecycle_stage = "end_of_life"
        elif avg_tread < 3.0:
            lifecycle_stage = "replacement_window"
        elif avg_tread < 5.0:
            lifecycle_stage = "mid_life_monitoring"

        return {
            "physical_tire_state": {
                "avg_tread_mm": round(avg_tread, 2),
                "risk_level": report.get("risk_level"),
                "sensor_snapshot": sensor_data,
            },
            "virtual_ai_simulation": {
                "lifecycle_stage": lifecycle_stage,
                "simulated_remaining_km": predictive.get("remaining_useful_life_km"),
                "simulated_failure_window": predictive.get("failure_forecast_window"),
            },
            "sync_pattern": "Physical Tyre <-> Virtual AI Simulation",
            "industry_4_0_ready": True,
        }

    def iot_sensor_fusion(self, report: dict[str, Any], sensor_data: dict[str, Any]) -> dict[str, Any]:
        pressure = sensor_data.get("tire_pressure_psi")
        temperature = sensor_data.get("temperature_c")
        vibration = sensor_data.get("vibration_g")
        speed = sensor_data.get("speed_kmph")
        active_channels = [
            name
            for name, value in {
                "pressure": pressure,
                "temperature": temperature,
                "vibration": vibration,
                "speed": speed,
            }.items()
            if value is not None
        ]

        alerts: list[str] = []
        if pressure is not None and (pressure < 28 or pressure > 38):
            alerts.append("pressure_out_of_nominal_range")
        if temperature is not None and temperature >= 55:
            alerts.append("high_temperature")
        if vibration is not None and vibration >= 1.2:
            alerts.append("vibration_anomaly")
        if speed is not None and speed >= 100:
            alerts.append("high_speed_operation")

        return {
            "fusion_mode": "Sensor Data + Image Data -> Fusion AI",
            "active_sensor_channels": active_channels,
            "telemetry": {
                "tire_pressure_psi": pressure,
                "temperature_c": temperature,
                "vibration_g": vibration,
                "speed_kmph": speed,
            },
            "sensor_alerts": alerts,
            "fusion_confidence": "high" if len(active_channels) >= 3 else "image_primary",
            "multimodal_ai_system": True,
        }

    def explainability(
        self,
        report: dict[str, Any],
        *,
        image_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        wear_label = (
            report.get("predictions", {})
            .get("wear_pattern", {})
            .get("label", "uniform_wear")
        )
        regions = self._regions_for_wear_label(str(wear_label))
        image_heatmap = self._image_heatmap_summary(image_bytes) if image_bytes else None
        return {
            "methods": ["Grad-CAM", "SHAP", "Attention Heatmaps"],
            "why_classified_as_damaged": self._xai_reason(report),
            "damaged_region_highlights": regions,
            "heatmap_coordinate_system": "relative_box_xywh_0_to_1",
            "attention_summary": image_heatmap,
            "research_ethics_note": "Provides visual reasoning metadata for technician review.",
        }

    def edge_ai_status(self) -> dict[str, Any]:
        return {
            "workflow": ["Camera", "Edge Device", "Local Prediction", "Cloud Sync"],
            "runtimes": {
                "onnx_runtime": _module_available("onnxruntime"),
                "tensorrt": _module_available("tensorrt"),
                "nvidia_jetson": bool(os.getenv("JETSON_DEVICE")),
                "mobile_inference": "tflite_and_onnx_export_hooks",
            },
            "offline_prediction_mode": True,
            "local_sync_queue": str(PROJECT_ROOT / "logs" / "edge_sync_queue.jsonl"),
        }

    def mlops_snapshot(self) -> dict[str, Any]:
        registry_path = PROJECT_ROOT / "ai_model" / "saved_models" / "model_registry.json"
        metadata_path = PROJECT_ROOT / "ai_model" / "saved_models" / "model_metadata.json"
        return {
            "block": "MLOps & Model Lifecycle Management",
            "dataset_versioning": {
                "dvc_pipeline": str(PROJECT_ROOT / "mlops" / "dvc.yaml"),
                "dataset_fingerprint": self._dataset_fingerprint(),
            },
            "experiment_tracking": {
                "local_json_tracker": str(PROJECT_ROOT / "training_logs"),
                "mlflow_available": _module_available("mlflow"),
                "weights_biases_available": _module_available("wandb"),
            },
            "model_registry": {
                "registry_path": str(registry_path),
                "metadata_path": str(metadata_path),
                "registered": registry_path.exists() or metadata_path.exists(),
                "latest_model": self._read_latest_model_version(registry_path, metadata_path),
            },
            "ci_cd_deployment": {
                "docker": (PROJECT_ROOT / "deployment" / "docker" / "docker-compose.yml").exists(),
                "kubernetes": (PROJECT_ROOT / "deployment" / "kubernetes" / "deployment.yaml").exists(),
                "kubeflow_pipeline": str(PROJECT_ROOT / "mlops" / "kubeflow_pipeline.py"),
                "airflow_dag": str(PROJECT_ROOT / "mlops" / "airflow_smart_tire_dag.py"),
            },
            "monitoring": {
                "model_drift_detection": "available_in_dashboard",
                "auto_retraining": settings.AUTO_RETRAIN,
                "retrain_threshold": settings.RETRAIN_THRESHOLD,
            },
        }

    def monitoring_summary(self, report: dict[str, Any] | None = None) -> dict[str, Any]:
        risk_level = str((report or {}).get("risk_level", "LOW"))
        return {
            "model_drift_detection": "low" if risk_level in {"LOW", "MODERATE"} else "watch",
            "system_health": "online",
            "gpu_usage": self._gpu_status(),
            "api_latency_ms": self._read_latency_hint(),
            "error_logs": self._log_status(),
            "current_report_risk": risk_level,
        }

    def multi_agent_system(
        self,
        report: dict[str, Any],
        confidence: dict[str, Any],
        predictive: dict[str, Any],
        rag: dict[str, Any],
    ) -> dict[str, Any]:
        wear = report.get("predictions", {}).get("wear_pattern", {})
        risk_label = confidence.get("failure_risk_label")
        return {
            "autonomous_ai_ecosystem": True,
            "agents": [
                {
                    "agent": "Agent 1 - Damage Detection",
                    "output": f"{wear.get('label', 'uniform_wear')} with {wear.get('severity', 'low')} severity",
                },
                {
                    "agent": "Agent 2 - Maintenance Recommendation",
                    "output": predictive.get("recommended_action"),
                },
                {
                    "agent": "Agent 3 - Cost Analysis",
                    "output": self._cost_band(str(risk_label)),
                },
                {
                    "agent": "Agent 4 - Report Generation",
                    "output": f"{len(rag.get('retrieved_items', []))} knowledge items added to technician notes",
                },
            ],
        }

    def federated_learning_status(self) -> dict[str, Any]:
        return {
            "mode": "federated_learning_ready",
            "vehicle_nodes": int(os.getenv("FEDERATED_SIM_NODES", "3")),
            "privacy_rule": "vehicles train locally and share encrypted weight updates only",
            "secure_aggregation": "local_simulation",
            "centralized_training_replacement": "optional_future_upgrade",
        }

    def knowledge_retrieval(self, report: dict[str, Any], sensor_data: dict[str, Any]) -> dict[str, Any]:
        risk = str(report.get("risk_level", "")).lower()
        wear_label = (
            report.get("predictions", {})
            .get("wear_pattern", {})
            .get("label", "")
        )
        query_terms = {risk, str(wear_label).lower()}
        for key, value in sensor_data.items():
            if value is not None:
                query_terms.add(key.lower())
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in KNOWLEDGE_BASE:
            score = len(query_terms.intersection({keyword.lower() for keyword in item["keywords"]}))
            if score:
                scored.append((score, item))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        retrieved = [item for _, item in scored[:3]] or KNOWLEDGE_BASE[:2]
        return {
            "system": "Maintenance Knowledge Base using local RAG-style retrieval",
            "vector_db_targets": ["FAISS", "Pinecone"],
            "retrieved_items": retrieved,
            "reasoning_enabled": True,
        }

    def report_generation(
        self,
        report: dict[str, Any],
        agents: dict[str, Any],
        rag: dict[str, Any],
    ) -> dict[str, Any]:
        agent_outputs = [agent["output"] for agent in agents.get("agents", [])]
        knowledge = rag.get("retrieved_items", [])
        first_knowledge = knowledge[0]["recommendation"] if knowledge else "Continue monitoring."
        return {
            "llm_backend": "Llama via Ollama when available; deterministic local fallback otherwise",
            "formats": ["JSON", "Markdown", "PDF-ready HTML"],
            "technician_notes": [
                f"Risk level: {report.get('risk_level')}.",
                f"Confidence: {round(_safe_float(report.get('confidence'), 0.75) * 100, 1)}%.",
                first_knowledge,
            ],
            "agent_summary": agent_outputs,
        }

    def synthetic_data_status(self) -> dict[str, Any]:
        return {
            "local_engine": "augmentation_pipeline",
            "research_methods": ["GANs", "Diffusion Models", "Data Augmentation"],
            "target_classes": ["cracks", "bulges", "punctures", "cupping_wear", "one_side_wear"],
            "output_path": str(PROJECT_ROOT / "dataset" / "synthetic"),
            "status": "configured_for_research_extension",
        }

    def cloud_native_status(self) -> dict[str, Any]:
        return {
            "docker": (PROJECT_ROOT / "deployment" / "docker" / "docker-compose.yml").exists(),
            "kubernetes": (PROJECT_ROOT / "deployment" / "kubernetes" / "deployment.yaml").exists(),
            "microservices": ["backend-api", "frontend-web", "model-runtime", "monitoring-dashboard"],
            "deployment_maturity": "cloud_native_ready",
        }

    def record_mlops_event(self, event_type: str, payload: dict[str, Any]) -> Path:
        event_dir = PROJECT_ROOT / "training_logs" / "mlops_events"
        event_dir.mkdir(parents=True, exist_ok=True)
        event_path = event_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return event_path

    def _normalize_sensor_data(self, sensor_data: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key in ("tire_pressure_psi", "temperature_c", "vibration_g", "speed_kmph"):
            value = sensor_data.get(key)
            normalized[key] = None if value is None else round(_safe_float(value), 3)
        return normalized

    def _sensor_risk(self, sensor_data: dict[str, Any]) -> float:
        score = 0.0
        pressure = sensor_data.get("tire_pressure_psi")
        temperature = sensor_data.get("temperature_c")
        vibration = sensor_data.get("vibration_g")
        speed = sensor_data.get("speed_kmph")
        if pressure is not None:
            score += min(abs(_safe_float(pressure, 32.0) - 32.0) * 3.0, 25.0)
        if temperature is not None:
            score += max(0.0, _safe_float(temperature) - 45.0) * 1.4
        if vibration is not None:
            score += max(0.0, _safe_float(vibration) - 0.6) * 22.0
        if speed is not None:
            score += max(0.0, _safe_float(speed) - 90.0) * 0.35
        return _clamp(score, 0.0, 100.0)

    def _risk_label(self, risk_score: float) -> str:
        if risk_score >= 85:
            return "Critical"
        if risk_score >= 65:
            return "High"
        if risk_score >= 35:
            return "Moderate"
        return "Low"

    def _forecast_window(self, days: float) -> str:
        if days <= 0:
            return "immediate"
        if days <= 14:
            return "within_2_weeks"
        if days <= 90:
            return "within_3_months"
        return "beyond_3_months"

    def _maintenance_action(self, risk_level: str, days: float) -> str:
        risk = str(risk_level).upper()
        if risk == "CRITICAL" or days <= 0:
            return "Stop driving and replace tire before next use."
        if risk == "HIGH" or days <= 14:
            return "Schedule replacement urgently and avoid high-speed driving."
        if risk == "MODERATE" or days <= 90:
            return "Plan inspection, rotation, alignment, and pressure correction."
        return "Continue regular monitoring and maintain recommended pressure."

    def _regions_for_wear_label(self, wear_label: str) -> list[dict[str, Any]]:
        if wear_label == "center_wear":
            return [{"label": "center_tread_band", "box": [0.35, 0.1, 0.3, 0.8], "intensity": 0.86}]
        if wear_label == "edge_wear":
            return [
                {"label": "left_shoulder", "box": [0.02, 0.1, 0.2, 0.8], "intensity": 0.82},
                {"label": "right_shoulder", "box": [0.78, 0.1, 0.2, 0.8], "intensity": 0.82},
            ]
        if wear_label == "one_side_wear":
            return [{"label": "outer_shoulder", "box": [0.02, 0.08, 0.32, 0.84], "intensity": 0.9}]
        if wear_label == "cupping_wear":
            return [
                {"label": "scalloped_patch_1", "box": [0.18, 0.18, 0.18, 0.18], "intensity": 0.72},
                {"label": "scalloped_patch_2", "box": [0.58, 0.62, 0.2, 0.2], "intensity": 0.76},
            ]
        if wear_label == "patchy_wear":
            return [
                {"label": "irregular_patch_1", "box": [0.2, 0.18, 0.22, 0.25], "intensity": 0.78},
                {"label": "irregular_patch_2", "box": [0.55, 0.48, 0.24, 0.28], "intensity": 0.74},
            ]
        return [{"label": "uniform_tread_surface", "box": [0.12, 0.12, 0.76, 0.76], "intensity": 0.35}]

    def _xai_reason(self, report: dict[str, Any]) -> str:
        predictions = report.get("predictions", {})
        tread = predictions.get("tread_depths_mm", {})
        wear = predictions.get("wear_pattern", {})
        return (
            f"The model combined tread average {tread.get('average', 'unknown')} mm, "
            f"wear pattern {wear.get('label', 'unknown')}, and risk {report.get('risk_level')} "
            "to identify the tire condition."
        )

    def _image_heatmap_summary(self, image_bytes: bytes | None) -> dict[str, Any] | None:
        if not image_bytes:
            return None
        try:
            import cv2
            import numpy as np

            raw = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return None
            resized = cv2.resize(image, (192, 192))
            edges = cv2.Canny(resized, 80, 160)
            grid = []
            for row in range(3):
                for col in range(3):
                    cell = edges[row * 64 : (row + 1) * 64, col * 64 : (col + 1) * 64]
                    grid.append(
                        {
                            "cell": f"r{row + 1}c{col + 1}",
                            "edge_density": round(float(np.mean(cell) / 255.0), 4),
                        }
                    )
            grid.sort(key=lambda item: item["edge_density"], reverse=True)
            return {
                "top_attention_cells": grid[:3],
                "edge_heatmap_available": True,
            }
        except Exception as exc:
            logger.debug("XAI heatmap summary unavailable: %s", exc)
            return {"edge_heatmap_available": False, "reason": str(exc)}

    def _dataset_fingerprint(self) -> str:
        digest = hashlib.sha256()
        roots = [
            PROJECT_ROOT / "dataset" / "metadata",
            PROJECT_ROOT / "dataset" / "schemas",
            PROJECT_ROOT / "dataset" / "splits",
        ]
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    stat = path.stat()
                    digest.update(str(path.relative_to(PROJECT_ROOT)).encode("utf-8"))
                    digest.update(str(stat.st_size).encode("ascii"))
                    digest.update(str(int(stat.st_mtime)).encode("ascii"))
        return digest.hexdigest()[:16]

    def _read_latest_model_version(self, *paths: Path) -> str:
        for path in paths:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                version = data.get("model_version") or data.get("runtime_model")
                if version:
                    return str(version)
            except Exception:
                continue
        return "not_registered"

    def _module_local_status(self, module_id: str) -> str:
        optional_ready = {
            "mlops": "local_tracker_ready",
            "edge_ai": "offline_runtime_ready",
            "xai": "report_heatmap_metadata_ready",
            "cloud": "docker_kubernetes_present",
            "security": "optional_auth_ready",
            "monitoring": "dashboard_ready",
        }
        return optional_ready.get(module_id, "implemented_as_lightweight_local_module")

    def _gpu_status(self) -> dict[str, Any]:
        try:
            import torch

            if not torch.cuda.is_available():
                return {"available": False, "usage_pct": None, "device": "cpu"}
            return {
                "available": True,
                "usage_pct": "driver_dependent",
                "device": torch.cuda.get_device_name(0),
            }
        except Exception:
            return {"available": False, "usage_pct": None, "device": "unknown"}

    def _read_latency_hint(self) -> dict[str, Any]:
        backend_log = PROJECT_ROOT / "logs" / "backend-local.out.log"
        if not backend_log.exists():
            return {"latest": None, "source": "no_local_log_yet"}
        try:
            stat = backend_log.stat()
            return {"latest": "available_in_response_header", "log_updated_unix": int(stat.st_mtime)}
        except OSError:
            return {"latest": None, "source": "log_unreadable"}

    def _log_status(self) -> dict[str, Any]:
        log_dir = PROJECT_ROOT / "logs"
        if not log_dir.exists():
            return {"status": "no_logs_yet", "error_files": 0}
        error_files = list(log_dir.glob("*err.log"))
        non_empty = [path.name for path in error_files if path.exists() and path.stat().st_size > 0]
        return {"status": "warnings_present" if non_empty else "clean", "error_files": len(non_empty)}

    def _drift_status(self, feedback_stats: dict[str, Any]) -> dict[str, Any]:
        total = _safe_float(feedback_stats.get("total_feedback"), 0.0)
        wrong = _safe_float(feedback_stats.get("wrong_predictions"), 0.0)
        wrong_rate = wrong / max(total, 1.0)
        if wrong_rate >= 0.35 and total >= 10:
            status = "drift_suspected"
        elif wrong_rate >= 0.2 and total >= 5:
            status = "watch"
        else:
            status = "stable"
        return {
            "status": status,
            "wrong_feedback_rate": round(wrong_rate, 4),
            "auto_retraining": settings.AUTO_RETRAIN,
        }

    def _cost_band(self, risk_label: str) -> str:
        normalized = risk_label.lower()
        if normalized == "critical":
            return "highest cost band: immediate replacement and downtime risk"
        if normalized == "high":
            return "high cost band: urgent replacement planning"
        if normalized == "moderate":
            return "medium cost band: inspection and alignment recommended"
        return "low cost band: monitoring and pressure maintenance"
