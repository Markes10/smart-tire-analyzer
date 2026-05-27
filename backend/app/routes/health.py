"""
Backend health and readiness routes.
"""

import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.database.db import ensure_database_ready
from app.services.api_key_rotator import (
    get_gemini_rotator,
    get_weather_rotator,
    get_maps_rotator,
    get_mapillary_rotator,
)

logger = logging.getLogger(__name__)
router = APIRouter()
_start_time = time.time()
APP_VERSION = "1.0.0"


def _json_safe_attr(obj: object, name: str, default: object = "not_loaded") -> object:
    value = getattr(obj, name, default)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _model_component(request: Request) -> dict:
    inference_svc = getattr(request.app.state, "inference_service", None)
    model_ready = bool(inference_svc and inference_svc.is_ready())
    metadata = getattr(inference_svc, "_hybrid_metadata", {}) if inference_svc else {}
    acceptance = metadata.get("acceptance") if isinstance(metadata, dict) else None
    return {
        "status": "ready" if model_ready else "not_loaded",
        "version": _json_safe_attr(inference_svc, "_model_version") if inference_svc else "not_loaded",
        "source": _json_safe_attr(inference_svc, "_model_source") if inference_svc else "not_loaded",
        "checkpoint": _json_safe_attr(inference_svc, "_model_checkpoint", None) if inference_svc else None,
        "checkpoint_status": metadata.get("runtime_checkpoint_status") if isinstance(metadata, dict) else None,
        "acceptance_passed": acceptance.get("passed") if isinstance(acceptance, dict) else None,
        "load_error": _json_safe_attr(inference_svc, "_load_error", None) if inference_svc else None,
    }


@router.get("", summary="Liveness probe")
async def liveness(request: Request):
    """Return a lightweight status summary for the running service."""
    model_component = _model_component(request)
    model_ready = model_component["status"] == "ready"

    return JSONResponse(
        content={
            "status": "alive" if model_ready else "starting",
            "version": APP_VERSION,
            "uptime_seconds": round(time.time() - _start_time, 1),
            "components": {
                "api": "ready",
                "model": model_component["status"],
                "model_version": model_component["version"],
                "model_source": model_component["source"],
                "model_checkpoint": model_component["checkpoint"],
                "model_checkpoint_status": model_component["checkpoint_status"],
                "model_acceptance_passed": model_component["acceptance_passed"],
                "model_load_error": model_component["load_error"],
            },
        }
    )


@router.get("/ready", summary="Readiness probe")
async def readiness(request: Request):
    """
    Readiness check — verifies DB connection and AI model are loaded.
    Returns 200 when ready to serve traffic, 503 when not.
    """
    checks = {}

    # Check AI model
    try:
        model_component = _model_component(request)
        checks["model"] = model_component["status"]
    except Exception as e:
        model_component = {"load_error": str(e)}
        checks["model"] = f"error: {e}"

    # Check DB
    try:
        await ensure_database_ready()
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ready = all(v == "ready" for v in checks.values())
    status_code = 200 if all_ready else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "version": APP_VERSION,
            "components": checks,
            "checks": checks,
            "model": model_component,
            "uptime_seconds": round(time.time() - _start_time, 1),
        },
    )


@router.get("/api-keys", summary="API key rotation status")
async def api_key_status(request: Request):
    """
    Get status of API key rotation for all services.
    Shows current usage, quotas, and any issues.
    """
    status = {
        "gemini": get_gemini_rotator().get_status() if get_gemini_rotator() else {"status": "not_initialized"},
        "weather": get_weather_rotator().get_status() if get_weather_rotator() else {"status": "not_initialized"},
        "maps": get_maps_rotator().get_status() if get_maps_rotator() else {"status": "not_initialized"},
        "mapillary": get_mapillary_rotator().get_status() if get_mapillary_rotator() else {"status": "not_initialized"},
    }

    # Check if any API has issues
    has_issues = False
    for api_status in status.values():
        if "keys" in api_status:
            for key_info in api_status["keys"].values():
                if not key_info.get("is_active") or key_info.get("is_quota_exceeded"):
                    has_issues = True
                    break

    return JSONResponse(
        status_code=200,
        content={
            "timestamp": time.time(),
            "status": "warning" if has_issues else "ok",
            "api_keys": status,
        },
    )
