import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import create_app
from app.services.enterprise_ai_service import EnterpriseAIService
from app.services.security_service import SecurityService


def _demo_report():
    return {
        "risk_level": "HIGH",
        "confidence": 0.92,
        "predictions": {
            "tread_depths_mm": {"average": 2.4, "min": 2.1, "max": 2.8},
            "remaining_life_km": 4500,
            "wear_pattern": {"label": "edge_wear", "severity": "high", "confidence": 0.9},
        },
    }


def test_enterprise_extensions_include_requested_blocks():
    payload = EnterpriseAIService().build_analysis_extensions(
        _demo_report(),
        sensor_data={
            "tire_pressure_psi": 27,
            "temperature_c": 56,
            "vibration_g": 1.5,
            "speed_kmph": 95,
        },
    )

    for key in (
        "mlops_lifecycle",
        "edge_ai",
        "explainable_ai",
        "confidence_estimation",
        "digital_twin",
        "predictive_maintenance",
        "iot_sensor_fusion",
        "cloud_native",
        "security",
        "monitoring",
        "multi_agent_ai",
        "federated_learning",
        "rag_knowledge_base",
        "llm_report_generator",
        "synthetic_data_engine",
    ):
        assert key in payload


def test_security_demo_token_round_trip():
    service = SecurityService(secret="test-secret")
    token = service.create_demo_token(role="technician")
    verification = service.verify_token(token)
    assert verification["valid"] is True
    assert verification["claims"]["role"] == "technician"


def test_enterprise_routes_are_available():
    client = TestClient(create_app())
    architecture = client.get("/enterprise/architecture")
    assert architecture.status_code == 200
    assert len(architecture.json()["modules"]) >= 15

    simulation = client.post("/enterprise/simulate", json={"risk_level": "HIGH"})
    assert simulation.status_code == 200
    assert simulation.json()["multi_agent_ai"]["autonomous_ai_ecosystem"] is True
