"""
Backend Routes — History Endpoint
GET /history        — Paginated scan history  
GET /history/{id}   — Single session by ID
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from app.database.crud import get_analysis_history, get_analysis_by_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "",
    summary="Get analysis history",
    description="Return paginated tire analysis history with optional risk level filter.",
)
async def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MODERATE, HIGH, CRITICAL"),
    from_date: Optional[str] = Query(None, description="ISO 8601 start date filter"),
    to_date: Optional[str] = Query(None, description="ISO 8601 end date filter"),
):
    data = await get_analysis_history(
        page=page,
        page_size=page_size,
        risk_level=risk_level,
        from_date=from_date,
        to_date=to_date,
    )
    return JSONResponse(content=data)


@router.get(
    "/{session_id}",
    summary="Get analysis by session ID",
)
async def get_single(session_id: str):
    record = await get_analysis_by_session(session_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return JSONResponse(content=record)
