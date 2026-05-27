"""
POST /analyze - tire image upload, preprocessing, AI inference, and report building.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.database.crud import save_analysis_result
from app.models.response_models import AnalysisResponse
from app.routes.metrics import record_analyze_request
from app.services.gemini_service import GeminiService
from app.services.continuous_learning_service import save_analysis_sample
from app.services.enterprise_ai_service import EnterpriseAIService
from app.services.inference_service import InferenceService
from app.services.maps_service import MapsService
from app.services.notifications import NotificationService
from app.services.ollama_service import OllamaService
from app.services.ocr_training_service import OCRTrainingService
from app.services.report_service import ReportService
from app.services.sidewall_service import SidewallService
from app.services.weather_service import WeatherService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.image_optimizer import optimize_image_bytes

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


def get_inference_service(request: Request) -> InferenceService:
    svc = getattr(request.app.state, "inference_service", None)
    if svc is None:
        svc = InferenceService()
        svc._load_model()
        request.app.state.inference_service = svc
    return svc


async def _load_context(
    latitude: float | None,
    longitude: float | None,
    session_id: str,
    source_latitude: float | None = None,
    source_longitude: float | None = None,
    destination_latitude: float | None = None,
    destination_longitude: float | None = None,
) -> dict:
    has_route = all(
        value is not None
        for value in (
            source_latitude,
            source_longitude,
            destination_latitude,
            destination_longitude,
        )
    )

    if not has_route and (latitude is None or longitude is None):
        return {}

    try:
        maps_svc = MapsService()
        weather_svc = WeatherService()
        if has_route:
            assert source_latitude is not None
            assert source_longitude is not None
            assert destination_latitude is not None
            assert destination_longitude is not None
            context_latitude = (source_latitude + destination_latitude) / 2
            context_longitude = (source_longitude + destination_longitude) / 2
            maps_task = maps_svc.get_route_road_context(
                source_latitude,
                source_longitude,
                destination_latitude,
                destination_longitude,
            )
        else:
            assert latitude is not None
            assert longitude is not None
            context_latitude = latitude
            context_longitude = longitude
            maps_task = maps_svc.get_road_context(latitude, longitude)

        maps_data, weather_data = await asyncio.gather(
            maps_task,
            weather_svc.get_weather(context_latitude, context_longitude),
            return_exceptions=True,
        )
    except Exception as exc:
        logger.warning("[%s] Context fetch failed (non-fatal): %s", session_id, exc)
        return {}

    context: dict = {}
    if isinstance(maps_data, dict):
        context.update(maps_data)
    if isinstance(weather_data, dict):
        context.update(weather_data)
    return context


@router.post(
    "",
    response_model=AnalysisResponse,
    summary="Analyze tire image",
    description=(
        "Upload a tread image and optional sidewall image. Returns tread depth, "
        "health score, remaining life, wear pattern, sidewall details, and driving recommendations."
    ),
)
async def analyze_tire(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Tread / front-view tire image"),
    sidewall_image: Optional[UploadFile] = File(None, description="Optional sidewall photo"),
    latitude: Optional[float] = Form(None, description="GPS latitude for road/weather context"),
    longitude: Optional[float] = Form(None, description="GPS longitude for road/weather context"),
    source_latitude: Optional[float] = Form(None, description="Route source latitude"),
    source_longitude: Optional[float] = Form(None, description="Route source longitude"),
    destination_latitude: Optional[float] = Form(None, description="Route destination latitude"),
    destination_longitude: Optional[float] = Form(None, description="Route destination longitude"),
    tire_brand: Optional[str] = Form(None, description="User-provided brand hint"),
    tire_model: Optional[str] = Form(None, description="User-provided model hint"),
    tire_size: Optional[str] = Form(None, description="User-provided size hint"),
    mileage_km: Optional[float] = Form(None, description="Current vehicle mileage in km"),
    tire_pressure_psi: Optional[float] = Form(None, description="Optional IoT tire pressure reading"),
    temperature_c: Optional[float] = Form(None, description="Optional IoT tire temperature reading"),
    vibration_g: Optional[float] = Form(None, description="Optional IoT vibration reading"),
    speed_kmph: Optional[float] = Form(None, description="Optional vehicle speed reading"),
    inference_svc: InferenceService = Depends(get_inference_service),
):
    session_id = str(uuid.uuid4())
    started_at = time.time()
    analyze_status = "success"
    logger.info("[%s] Analysis request received: %s", session_id, image.filename)

    try:
        if image.content_type not in _ALLOWED_CONTENT_TYPES:
            analyze_status = "invalid_content_type"
            raise HTTPException(status_code=422, detail="Image must be JPEG, PNG, or WebP")

        image_bytes = await image.read()
        if len(image_bytes) > _MAX_IMAGE_BYTES:
            analyze_status = "payload_too_large"
            raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")

        if settings.IMAGE_OPTIMIZER_ENABLED:
            optimized = optimize_image_bytes(
                image_bytes,
                content_type=image.content_type,
                max_dimension=settings.IMAGE_OPTIMIZER_MAX_DIMENSION,
            )
            image_bytes = optimized.data
            image_content_type = optimized.content_type
        else:
            image_content_type = image.content_type or "image/jpeg"

        sidewall_bytes: bytes | None = None
        sidewall_mime = "image/jpeg"
        if sidewall_image is not None:
            if sidewall_image.content_type not in _ALLOWED_CONTENT_TYPES:
                analyze_status = "invalid_sidewall_type"
                raise HTTPException(status_code=422, detail="Sidewall image must be JPEG, PNG, or WebP")
            sidewall_bytes = await sidewall_image.read()
            if len(sidewall_bytes) > _MAX_IMAGE_BYTES:
                analyze_status = "sidewall_too_large"
                raise HTTPException(status_code=413, detail="Sidewall image exceeds 10 MB limit")
            if settings.IMAGE_OPTIMIZER_ENABLED:
                optimized_sidewall = optimize_image_bytes(
                    sidewall_bytes,
                    content_type=sidewall_image.content_type,
                    max_dimension=settings.IMAGE_OPTIMIZER_MAX_DIMENSION,
                )
                sidewall_bytes = optimized_sidewall.data
                sidewall_mime = optimized_sidewall.content_type
            else:
                sidewall_mime = sidewall_image.content_type or "image/jpeg"
            logger.info("[%s] Sidewall image provided: %s", session_id, sidewall_image.filename)

        sidewall_task = None
        if sidewall_bytes:
            sidewall_task = asyncio.create_task(
                SidewallService().extract_tire_details(sidewall_bytes, mime_type=sidewall_mime)
            )

        context_data = await _load_context(
            latitude,
            longitude,
            session_id,
            source_latitude=source_latitude,
            source_longitude=source_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
        )

        try:
            prediction_result = await inference_svc.predict(
                image_bytes=image_bytes,
                session_id=session_id,
                context_data=context_data,
            )
        except ValueError as exc:
            analyze_status = "rejected"
            logger.warning("[%s] Image rejected: %s", session_id, exc)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if prediction_result.get("rejected"):
            analyze_status = "rejected"
            reason = str(prediction_result.get("reason") or "")
            if "hybrid model is unavailable" in reason.lower():
                analyze_status = "model_unavailable"
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Trained hybrid model is unavailable",
                        "model_version": prediction_result.get("model_version"),
                        "source": prediction_result.get("source"),
                    },
                )
            blur_score = prediction_result.get("blur_score")
            blur_threshold = prediction_result.get("blur_threshold")
            blur_detail = (
                f"blur score: {blur_score:.0f}, minimum: {blur_threshold:.0f}"
                if isinstance(blur_score, (int, float)) and isinstance(blur_threshold, (int, float))
                else "image could not be processed"
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Image quality too low ({blur_detail}). "
                    "Please retake the photo in good lighting."
                ),
            )

        sidewall_details: dict = {}
        if sidewall_task is not None:
            try:
                sidewall_details = await sidewall_task
            except Exception as exc:
                logger.warning("[%s] Sidewall extraction failed (non-fatal): %s", session_id, exc)
                sidewall_details = {"source": "error", "extraction_notes": str(exc)}

        try:
            reasoning = await OllamaService().reason(predictions=prediction_result, context=context_data)
        except Exception as exc:
            logger.warning("[%s] Ollama reasoning failed, trying Gemini: %s", session_id, exc)
            reasoning = None

        if reasoning is None:
            try:
                reasoning = await GeminiService().reason(predictions=prediction_result, context=context_data)
            except Exception as exc:
                logger.warning("[%s] Gemini reasoning failed, using fallback: %s", session_id, exc)
                reasoning = None

        metadata = {
            "tire_brand": tire_brand,
            "tire_model": tire_model,
            "tire_size": tire_size,
            "mileage_km": mileage_km,
            "tire_pressure_psi": tire_pressure_psi,
            "temperature_c": temperature_c,
            "vibration_g": vibration_g,
            "speed_kmph": speed_kmph,
            "image_filename": image.filename,
            "sidewall_image_filename": sidewall_image.filename if sidewall_image else None,
            "latitude": latitude,
            "longitude": longitude,
            "source_latitude": source_latitude,
            "source_longitude": source_longitude,
            "destination_latitude": destination_latitude,
            "destination_longitude": destination_longitude,
        }
        if sidewall_details:
            sidewall_size = sidewall_details.get("tire_size")
            if isinstance(sidewall_size, dict):
                sidewall_size = sidewall_size.get("full_formatted") or sidewall_size.get("raw")

            metadata["sidewall_details"] = sidewall_details
            metadata["tire_brand"] = tire_brand or sidewall_details.get("brand")
            metadata["tire_model"] = tire_model or sidewall_details.get("tire_model")
            metadata["tire_size"] = tire_size or sidewall_size

        final_report = ReportService().build_report(
            session_id=session_id,
            prediction_result=prediction_result,
            context=context_data,
            gemini_reasoning=reasoning,
            metadata=metadata,
        )
        sensor_data = {
            "tire_pressure_psi": tire_pressure_psi,
            "temperature_c": temperature_c,
            "vibration_g": vibration_g,
            "speed_kmph": speed_kmph,
        }
        final_report["enterprise_ai"] = EnterpriseAIService().build_analysis_extensions(
            final_report,
            image_bytes=image_bytes,
            sensor_data=sensor_data,
        )

        try:
            continuous_paths = save_analysis_sample(
                session_id=session_id,
                image_bytes=image_bytes,
                filename=image.filename,
                content_type=image_content_type,
                report=final_report,
            )
            final_report.setdefault("metadata", {}).update(continuous_paths)
        except Exception as exc:
            logger.warning("[%s] Continuous-learning image save failed (non-fatal): %s", session_id, exc)

        if sidewall_bytes and sidewall_details and sidewall_details.get("source") != "error":
            OCRTrainingService().add_example(sidewall_bytes, sidewall_details)

        background_tasks.add_task(save_analysis_result, final_report)

        risk_level = str(final_report.get("risk_level") or "")
        if risk_level in {"HIGH", "CRITICAL"}:
            predictions = final_report.get("predictions") or {}
            tread = predictions.get("tread_depths_mm") or {}
            background_tasks.add_task(
                NotificationService().notify_high_risk_analysis,
                session_id=session_id,
                risk_level=risk_level,
                health_score=predictions.get("health_score"),
                avg_tread_mm=tread.get("average"),
            )

        logger.info(
            "[%s] Analysis complete - health=%s risk=%s",
            session_id,
            final_report.get("predictions", {}).get("health_score"),
            final_report.get("risk_level"),
        )
        return JSONResponse(content=final_report)
    except HTTPException:
        if analyze_status == "success":
            analyze_status = "error"
        raise
    finally:
        record_analyze_request(status=analyze_status, duration_seconds=time.time() - started_at)
