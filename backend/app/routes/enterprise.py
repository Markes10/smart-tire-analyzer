"""
Enterprise architecture, monitoring, and lifecycle routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.database.crud import get_feedback_stats
from app.services.enterprise_ai_service import EnterpriseAIService
from app.services.security_service import SecurityService

router = APIRouter()


@router.get("/architecture", summary="Enterprise architecture map")
async def architecture():
    """Return the final-year-project enterprise architecture modules."""
    return JSONResponse(content=EnterpriseAIService().architecture_summary())


@router.get("/dashboard", summary="AI monitoring dashboard data")
async def dashboard():
    """Return monitoring, MLOps, deployment, edge, and security status."""
    try:
        feedback_stats = await get_feedback_stats()
    except Exception:
        feedback_stats = {}
    return JSONResponse(content=EnterpriseAIService().dashboard_payload(feedback_stats))


@router.post("/simulate", summary="Run local enterprise AI simulation")
async def simulate(
    payload: dict[str, Any] | None = Body(
        default=None,
        description="Optional report-like payload and IoT telemetry for local simulation.",
    )
):
    """Run the advanced extension layer against a lightweight demo report."""
    payload = payload or {}
    demo_report = payload.get("report") or {
        "risk_level": payload.get("risk_level", "HIGH"),
        "confidence": payload.get("confidence", 0.92),
        "predictions": {
            "tread_depths_mm": payload.get(
                "tread_depths_mm",
                {"average": 2.4, "min": 2.1, "max": 2.8},
            ),
            "remaining_life_km": payload.get("remaining_life_km", 4500),
            "wear_pattern": payload.get(
                "wear_pattern",
                {"label": "edge_wear", "severity": "high", "confidence": 0.91},
            ),
        },
    }
    sensor_data = payload.get("sensor_data") or {
        "tire_pressure_psi": payload.get("tire_pressure_psi"),
        "temperature_c": payload.get("temperature_c"),
        "vibration_g": payload.get("vibration_g"),
        "speed_kmph": payload.get("speed_kmph"),
    }
    return JSONResponse(
        content=EnterpriseAIService().build_analysis_extensions(
            demo_report,
            sensor_data=sensor_data,
        )
    )


@router.post("/mlops/event", summary="Record a local MLOps lifecycle event")
async def mlops_event(payload: dict[str, Any] | None = Body(default=None)):
    payload = payload or {}
    event_type = str(payload.get("event_type") or "manual_event")
    event_path = EnterpriseAIService().record_mlops_event(event_type, payload)
    return {
        "stored": True,
        "event_type": event_type,
        "path": str(event_path),
    }


@router.get("/security/demo-token", summary="Generate a local demo token")
async def demo_token(
    role: str = Query("technician", pattern="^(admin|ml_engineer|technician|viewer)$"),
    subject: str = Query("local-demo-user", min_length=1, max_length=80),
):
    token = SecurityService().create_demo_token(subject=subject, role=role)
    return {
        "token_type": "Bearer",
        "access_token": token,
        "role": role,
        "auth_enabled": False,
        "note": "Set AUTH_ENABLED=true to make the API require this bearer token.",
    }
