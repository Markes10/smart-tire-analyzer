"""
Model registry read-only API for admin UI and tooling.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / "ai_model" / "saved_models" / "model_registry.json"


@router.get("", summary="Read model registry")
async def get_model_registry():
    """Return the current model registry snapshot used by the runtime."""
    if not REGISTRY_PATH.exists():
        raise HTTPException(status_code=404, detail="Model registry not found. Train or promote a model first.")
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid model registry JSON: {exc}") from exc
    return JSONResponse(content=payload)
