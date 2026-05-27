"""
Prometheus metrics endpoint for scrape-based monitoring.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

router = APIRouter()

ANALYZE_REQUESTS = Counter(
    "smart_tire_analyze_requests_total",
    "Total tire analysis requests",
    ["status"],
)
ANALYZE_LATENCY = Histogram(
    "smart_tire_analyze_latency_seconds",
    "Tire analysis request latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
MODEL_READY = Gauge(
    "smart_tire_model_ready",
    "1 when the hybrid inference model is loaded and ready",
)
SERVICE_UPTIME = Gauge(
    "smart_tire_service_uptime_seconds",
    "Process uptime in seconds",
)

_START_TIME = time.time()


def record_analyze_request(*, status: str, duration_seconds: float) -> None:
    ANALYZE_REQUESTS.labels(status=status).inc()
    ANALYZE_LATENCY.observe(duration_seconds)


def refresh_runtime_gauges(request: Request) -> None:
    inference_svc = getattr(request.app.state, "inference_service", None)
    MODEL_READY.set(1 if inference_svc and inference_svc.is_ready() else 0)
    SERVICE_UPTIME.set(time.time() - _START_TIME)


@router.get("", summary="Prometheus metrics", include_in_schema=False)
async def metrics(request: Request):
    """Expose Prometheus scrape metrics."""
    refresh_runtime_gauges(request)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
