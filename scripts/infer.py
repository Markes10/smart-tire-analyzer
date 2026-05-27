"""
Local inference script for Smart Tire Analyzer.

Usage:
  python scripts/infer.py --image path/to/tire.jpg
  python scripts/infer.py --image path/to/tire.jpg --lat 28.6139 --lon 77.2090
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))


async def _load_context(latitude: float | None, longitude: float | None) -> dict:
    if latitude is None or longitude is None:
        return {}

    from app.services.maps_service import MapsService
    from app.services.weather_service import WeatherService

    maps_service = MapsService()
    weather_service = WeatherService()
    maps_data, weather_data = await asyncio.gather(
        maps_service.get_road_context(latitude, longitude),
        weather_service.get_weather(latitude, longitude),
        return_exceptions=True,
    )

    context: dict = {}
    if isinstance(maps_data, dict):
        context.update(maps_data)
    if isinstance(weather_data, dict):
        context.update(weather_data)
    return context


async def _build_reasoning(prediction: dict, context: dict) -> dict | None:
    from app.services.gemini_service import GeminiService

    service = GeminiService()
    try:
        return await service.reason(predictions=prediction, context=context)
    except Exception:
        return None


async def run_local_inference(image_path: Path, latitude: float | None, longitude: float | None) -> dict:
    from app.services.inference_service import InferenceService
    from app.services.report_service import ReportService

    image_bytes = image_path.read_bytes()

    inference_service = InferenceService()
    await inference_service.initialize()
    prediction = await inference_service.predict(image_bytes=image_bytes, session_id="local-cli")

    if prediction.get("rejected"):
        return prediction

    context = await _load_context(latitude, longitude)
    reasoning = await _build_reasoning(prediction, context)

    report_service = ReportService()
    report = report_service.build_report(
        session_id=prediction.get("session_id", "local-cli"),
        prediction_result=prediction,
        context=context,
        gemini_reasoning=reasoning,
        metadata={
            "image_filename": image_path.name,
            "latitude": latitude,
            "longitude": longitude,
        },
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Smart Tire inference locally")
    parser.add_argument("--image", required=True, help="Path to tire image")
    parser.add_argument("--lat", type=float, help="Latitude for context")
    parser.add_argument("--lon", type=float, help="Longitude for context")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    report = asyncio.run(run_local_inference(image_path, args.lat, args.lon))

    if report.get("rejected"):
        print(f"Image rejected: {report.get('reason', 'unknown reason')}")
        if report.get("blur_score") is not None:
            print(f"Blur score: {report['blur_score']:.2f}")
        return 1

    predictions = report["predictions"]
    tread = predictions["tread_depths_mm"]
    wear = predictions["wear_pattern"]

    print("=" * 56)
    print(" Smart Tire Analysis")
    print("=" * 56)
    print(f"Image:            {image_path.name}")
    print(f"Model version:    {report.get('model_version')}")
    print(f"Source:           {report.get('source')}")
    print(f"Risk level:       {report['risk_level']}")
    print(f"Health score:     {predictions['health_score']}/10")
    print(f"Average tread:    {tread['average']} mm")
    print(f"Remaining life:   {int(predictions['remaining_life_km']):,} km")
    print(f"Wear pattern:     {wear['label']} ({wear['severity']})")
    print(f"Confidence:       {report['confidence']:.2f}")
    print(f"Blur score:       {report.get('blur_score', 0.0)}")
    print("")
    print("Tread readings:")
    print(f"  T1={tread['tread_1']}  T2={tread['tread_2']}  T3={tread['tread_3']}  T4={tread['tread_4']}")

    if report.get("alerts"):
        print("")
        print("Alerts:")
        for alert in report["alerts"]:
            print(f"  [{alert['level']}] {alert['message']}")

    reasoning = report.get("reasoning") or {}
    if reasoning.get("driving_advice"):
        print("")
        print(f"Advice: {reasoning['driving_advice']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
