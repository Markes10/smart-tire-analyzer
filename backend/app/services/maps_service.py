"""
Maps Service - Google Maps, Street View, terrain, and route context.

The service keeps a no-key fallback for local development, but when Google
Maps keys are configured it can sample a selected route, inspect Street View
coverage/images, and summarize road context for tire safety reasoning.
"""

from __future__ import annotations

import asyncio
import io
import logging
import math
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

import aiohttp
import numpy as np
from PIL import Image

from app.config import settings
from app.services.api_key_rotator import APIKeyRotator, get_maps_rotator

logger = logging.getLogger(__name__)

ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
STREET_VIEW_METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
STREET_VIEW_IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"
MAX_ROUTE_SAMPLES = 5

Coord = Tuple[float, float]


class MapsService:
    def __init__(self):
        rot = get_maps_rotator()
        if not rot:
            keys = settings.get_maps_keys()
            rot = APIKeyRotator("maps", keys, daily_quota=settings.MAPS_DAILY_QUOTA) if keys else None

        self.rotator = rot
        self.enabled = bool(self.rotator and self.rotator.available_keys)
        if not self.enabled:
            logger.warning("No Maps API keys configured - using mock road context")

    async def get_road_context(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch point-level terrain, road condition, traffic, and Street View context.
        """
        if not self.enabled:
            return self._mock_context(lat, lon)

        try:
            elevation_data, street_view_meta = await asyncio.gather(
                self._fetch_elevation(lat, lon),
                self._fetch_street_view_metadata(lat, lon),
            )
            elevation_m = float(elevation_data.get("elevation", 100))
            terrain_type = self._classify_terrain(elevation_m)

            visual_summary = None
            if street_view_meta.get("status") == "OK":
                visual_summary = await self._fetch_street_view_visual(lat, lon, heading=0.0)

            sample = {
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation_m,
                "street_view": street_view_meta,
                "visual": visual_summary,
            }
            road_condition, road_basis = self._estimate_route_road_condition([sample], terrain_type)

            return {
                "terrain_type": terrain_type,
                "road_condition": road_condition,
                "road_condition_basis": road_basis,
                "traffic_density": "moderate",
                "elevation_m": elevation_m,
                "road_wear_multiplier": self._road_wear_mult(terrain_type, road_condition),
                "latitude": lat,
                "longitude": lon,
                "street_view_available": street_view_meta.get("status") == "OK",
                "street_view_sample_count": 1,
                "street_view_covered_samples": 1 if street_view_meta.get("status") == "OK" else 0,
                "street_view_visual_summary": self._build_street_view_summary([sample]),
                "street_view_samples": self._public_samples([sample]),
                "route_analysis_source": "single_point",
            }
        except Exception as e:
            logger.warning("Maps API error: %s - using mock", e)
            return self._mock_context(lat, lon)

    async def get_route_road_context(
        self,
        source_lat: float,
        source_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> Dict[str, Any]:
        """
        Analyze road context along a source-to-destination route.

        Uses Google Directions for route geometry when available. Samples the
        route, checks Street View metadata, extracts lightweight visual texture
        signals from Street View images, and returns a road condition summary.
        """
        if not self.enabled:
            return self._mock_route_context(source_lat, source_lon, destination_lat, destination_lon)

        try:
            route_points, route_meta = await self._fetch_route_points(
                source_lat,
                source_lon,
                destination_lat,
                destination_lon,
            )
            sampled_points = self._sample_points(route_points, MAX_ROUTE_SAMPLES)
            samples: List[Dict[str, Any]] = []

            for index, (lat, lon) in enumerate(sampled_points):
                next_point = self._neighbor_for_heading(sampled_points, index)
                heading = self._bearing_degrees((lat, lon), next_point) if next_point else 0.0
                samples.append(await self._analyze_route_sample(lat, lon, heading))

            elevations = [
                float(sample["elevation_m"])
                for sample in samples
                if isinstance(sample.get("elevation_m"), (int, float))
            ]
            terrain_type = self._classify_route_terrain(elevations)
            road_condition, road_basis = self._estimate_route_road_condition(samples, terrain_type)

            midpoint = sampled_points[len(sampled_points) // 2]
            return {
                "terrain_type": terrain_type,
                "road_condition": road_condition,
                "road_condition_basis": road_basis,
                "traffic_density": "moderate",
                "elevation_m": round(sum(elevations) / len(elevations), 2) if elevations else None,
                "road_wear_multiplier": self._road_wear_mult(terrain_type, road_condition),
                "latitude": midpoint[0],
                "longitude": midpoint[1],
                "route_source_latitude": source_lat,
                "route_source_longitude": source_lon,
                "route_destination_latitude": destination_lat,
                "route_destination_longitude": destination_lon,
                "route_distance_km": route_meta.get("distance_km"),
                "route_duration_min": route_meta.get("duration_min"),
                "route_analysis_source": route_meta.get("source", "linear_fallback"),
                "street_view_available": any(
                    sample.get("street_view", {}).get("status") == "OK" for sample in samples
                ),
                "street_view_sample_count": len(samples),
                "street_view_covered_samples": sum(
                    1 for sample in samples if sample.get("street_view", {}).get("status") == "OK"
                ),
                "street_view_visual_summary": self._build_street_view_summary(samples),
                "street_view_samples": self._public_samples(samples),
            }
        except Exception as e:
            logger.warning("Route Maps API error: %s - using mock route context", e)
            return self._mock_route_context(source_lat, source_lon, destination_lat, destination_lon)

    async def _analyze_route_sample(self, lat: float, lon: float, heading: float) -> Dict[str, Any]:
        elevation_data, street_view_meta = await asyncio.gather(
            self._fetch_elevation(lat, lon),
            self._fetch_street_view_metadata(lat, lon),
        )
        visual_summary = None
        if street_view_meta.get("status") == "OK":
            visual_summary = await self._fetch_street_view_visual(lat, lon, heading=heading)

        return {
            "latitude": lat,
            "longitude": lon,
            "elevation_m": elevation_data.get("elevation"),
            "street_view": street_view_meta,
            "visual": visual_summary,
        }

    async def _fetch_route_points(
        self,
        source_lat: float,
        source_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> Tuple[List[Coord], Dict[str, Any]]:
        data = await self._request_json(
            DIRECTIONS_URL,
            {
                "origin": f"{source_lat},{source_lon}",
                "destination": f"{destination_lat},{destination_lon}",
                "mode": "driving",
                "alternatives": "false",
            },
        )

        if data and data.get("status") == "OK":
            routes = data.get("routes", [])
            if routes:
                route = routes[0]
                encoded = route.get("overview_polyline", {}).get("points")
                points = self._decode_polyline(encoded) if encoded else []
                legs = route.get("legs", [])
                distance_m = sum(
                    leg.get("distance", {}).get("value", 0)
                    for leg in legs
                    if isinstance(leg, dict)
                )
                duration_s = sum(
                    leg.get("duration", {}).get("value", 0)
                    for leg in legs
                    if isinstance(leg, dict)
                )
                if points:
                    return points, {
                        "source": "google_directions",
                        "distance_km": round(distance_m / 1000, 2) if distance_m else None,
                        "duration_min": round(duration_s / 60, 1) if duration_s else None,
                    }

        return self._linear_route_points(source_lat, source_lon, destination_lat, destination_lon), {
            "source": "linear_fallback",
            "distance_km": round(
                self._haversine_km(source_lat, source_lon, destination_lat, destination_lon),
                2,
            ),
            "duration_min": None,
        }

    async def _fetch_elevation(self, lat: float, lon: float) -> Dict[str, Any]:
        if not self.enabled:
            return {"elevation": 50}

        data = await self._request_json(ELEVATION_URL, {"locations": f"{lat},{lon}"})
        if data:
            results = data.get("results", [])
            if isinstance(results, list) and results:
                res = results[0]
                if isinstance(res, dict):
                    return cast(Dict[str, Any], res)

        return {"elevation": 50}

    async def _fetch_street_view_metadata(self, lat: float, lon: float) -> Dict[str, Any]:
        data = await self._request_json(
            STREET_VIEW_METADATA_URL,
            {
                "location": f"{lat},{lon}",
                "source": "outdoor",
            },
        )
        if not data:
            return {"status": "UNAVAILABLE"}

        location = data.get("location") if isinstance(data.get("location"), dict) else {}
        return {
            "status": data.get("status", "UNKNOWN"),
            "pano_id": data.get("pano_id"),
            "date": data.get("date"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
        }

    async def _fetch_street_view_visual(
        self,
        lat: float,
        lon: float,
        heading: float,
    ) -> Optional[Dict[str, Any]]:
        image_bytes = await self._request_bytes(
            STREET_VIEW_IMAGE_URL,
            {
                "size": "640x640",
                "location": f"{lat},{lon}",
                "heading": f"{heading:.1f}",
                "pitch": "-12",
                "fov": "80",
                "source": "outdoor",
            },
        )
        if not image_bytes:
            return None
        return self._summarize_street_view_image(image_bytes)

    async def _request_json(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.rotator:
            return None

        attempts = 0
        max_attempts = max(1, len(self.rotator.available_keys))
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while attempts < max_attempts:
                key = self.rotator.get_current_key()
                if not key:
                    return None

                request_params = {**params, "key": key}
                try:
                    async with session.get(url, params=request_params) as resp:
                        resp.raise_for_status()
                        data = await resp.json()

                    status = str(data.get("status", "")).upper()
                    if status in {"OVER_QUERY_LIMIT", "REQUEST_DENIED"}:
                        self.rotator.record_error(key, status)
                        self.rotator.rotate_to_next_key()
                        attempts += 1
                        continue

                    self.rotator.record_successful_request(key)
                    return data if isinstance(data, dict) else None
                except aiohttp.ClientResponseError as e:
                    status = getattr(e, "status", None)
                    message = getattr(e, "message", "request failed")
                    logger.warning("Maps API HTTP error (status=%s): %s", status, message)
                    if status in (429, 403, 401):
                        self.rotator.record_error(key, f"HTTP {status}: {message}")
                        self.rotator.rotate_to_next_key()
                        attempts += 1
                        continue
                    raise
                except Exception as e:
                    logger.warning("Maps API error: %s", e)
                    self.rotator.record_error(key, str(e))
                    self.rotator.rotate_to_next_key()
                    attempts += 1

        return None

    async def _request_bytes(self, url: str, params: Dict[str, Any]) -> Optional[bytes]:
        if not self.enabled or not self.rotator:
            return None

        attempts = 0
        max_attempts = max(1, len(self.rotator.available_keys))
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while attempts < max_attempts:
                key = self.rotator.get_current_key()
                if not key:
                    return None

                request_params = {**params, "key": key}
                try:
                    async with session.get(url, params=request_params) as resp:
                        resp.raise_for_status()
                        body = await resp.read()
                    self.rotator.record_successful_request(key)
                    return body
                except aiohttp.ClientResponseError as e:
                    status = getattr(e, "status", None)
                    message = getattr(e, "message", "request failed")
                    logger.warning("Street View image HTTP error (status=%s): %s", status, message)
                    if status in (429, 403, 401):
                        self.rotator.record_error(key, f"HTTP {status}: {message}")
                        self.rotator.rotate_to_next_key()
                        attempts += 1
                        continue
                    raise
                except Exception as e:
                    logger.warning("Street View image error: %s", e)
                    self.rotator.record_error(key, str(e))
                    self.rotator.rotate_to_next_key()
                    attempts += 1

        return None

    def _summarize_street_view_image(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                gray = np.asarray(image.convert("L"), dtype=np.float32)
        except Exception as exc:
            logger.warning("Street View visual summary failed: %s", exc)
            return {"surface_texture": "unknown", "analysis_error": str(exc)}

        height = gray.shape[0]
        road_crop = gray[int(height * 0.55) :, :]
        if road_crop.size == 0:
            return {"surface_texture": "unknown", "analysis_error": "empty road crop"}

        grad_y, grad_x = np.gradient(road_crop)
        magnitude = np.sqrt((grad_x * grad_x) + (grad_y * grad_y))
        edge_density = float(np.mean(magnitude > 28.0))
        texture_score = float(np.percentile(magnitude, 85))
        brightness = float(np.mean(road_crop))

        if edge_density > 0.22 or texture_score > 42:
            surface_texture = "rough"
        elif edge_density > 0.12 or texture_score > 26:
            surface_texture = "mixed"
        else:
            surface_texture = "smooth"

        return {
            "surface_texture": surface_texture,
            "edge_density": round(edge_density, 4),
            "texture_score": round(texture_score, 2),
            "brightness": round(brightness, 1),
        }

    def _estimate_route_road_condition(
        self,
        samples: List[Dict[str, Any]],
        terrain_type: str,
    ) -> Tuple[str, str]:
        visuals = [
            sample.get("visual", {}).get("surface_texture")
            for sample in samples
            if isinstance(sample.get("visual"), dict)
        ]
        counts = Counter(texture for texture in visuals if texture)
        covered = sum(1 for sample in samples if sample.get("street_view", {}).get("status") == "OK")

        if counts.get("rough", 0) >= max(1, math.ceil(max(covered, 1) / 2)):
            return "poor", "Street View visual texture was rough on most covered samples."
        if counts.get("rough", 0) or counts.get("mixed", 0) >= 2:
            return "fair", "Street View visual texture showed mixed or rough surfaces."
        if terrain_type in {"hilly", "mountainous"}:
            return "fair", "Route terrain increases tire load even when the visible road surface looks acceptable."
        if covered > 0:
            return "good", "Street View coverage was available and visual texture looked mostly smooth."
        return "good", "Street View coverage was unavailable; using neutral road-condition default."

    def _build_street_view_summary(self, samples: List[Dict[str, Any]]) -> str:
        total = len(samples)
        covered = sum(1 for sample in samples if sample.get("street_view", {}).get("status") == "OK")
        textures = [
            sample.get("visual", {}).get("surface_texture")
            for sample in samples
            if isinstance(sample.get("visual"), dict)
        ]
        counts = Counter(texture for texture in textures if texture)
        if not total:
            return "No route samples were analyzed."
        if not covered:
            return f"Street View coverage was not available for {total} sampled point(s)."
        if not counts:
            return f"Street View coverage was available for {covered}/{total} sampled point(s), but visual texture could not be read."
        texture_text = ", ".join(f"{texture}: {count}" for texture, count in sorted(counts.items()))
        return f"Street View coverage {covered}/{total}; visual road texture signals: {texture_text}."

    def _public_samples(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        public: List[Dict[str, Any]] = []
        for sample in samples:
            street_view = sample.get("street_view", {}) if isinstance(sample.get("street_view"), dict) else {}
            visual = sample.get("visual", {}) if isinstance(sample.get("visual"), dict) else {}
            public.append(
                {
                    "latitude": sample.get("latitude"),
                    "longitude": sample.get("longitude"),
                    "elevation_m": sample.get("elevation_m"),
                    "street_view_status": street_view.get("status"),
                    "street_view_date": street_view.get("date"),
                    "surface_texture": visual.get("surface_texture"),
                    "edge_density": visual.get("edge_density"),
                    "texture_score": visual.get("texture_score"),
                }
            )
        return public

    def _classify_terrain(self, elevation_m: float) -> str:
        if elevation_m < 50:
            return "flat_urban"
        if elevation_m < 300:
            return "rolling_suburban"
        if elevation_m < 800:
            return "hilly"
        return "mountainous"

    def _classify_route_terrain(self, elevations: Iterable[float]) -> str:
        values = list(elevations)
        if not values:
            return "flat_urban"
        avg = sum(values) / len(values)
        elevation_range = max(values) - min(values)
        if elevation_range > 400 or avg >= 800:
            return "mountainous"
        if elevation_range > 160 or avg >= 300:
            return "hilly"
        return self._classify_terrain(avg)

    def _road_wear_mult(self, terrain: str, road_cond: str) -> float:
        """Higher multiplier = road degrades tires faster = less remaining life."""
        terrain_mult = {
            "flat_urban": 1.0,
            "rolling_suburban": 1.05,
            "hilly": 1.12,
            "mountainous": 1.25,
        }.get(terrain, 1.0)
        road_mult = {
            "excellent": 0.95,
            "good": 1.0,
            "fair": 1.1,
            "poor": 1.25,
        }.get(road_cond, 1.0)
        return round(terrain_mult * road_mult, 3)

    def _mock_context(self, lat: float, lon: float) -> Dict[str, Any]:
        return {
            "terrain_type": "flat_urban",
            "road_condition": "good",
            "road_condition_basis": "No Maps key configured; using neutral road-condition default.",
            "traffic_density": "moderate",
            "elevation_m": None,
            "road_wear_multiplier": 1.0,
            "latitude": lat,
            "longitude": lon,
            "street_view_available": False,
            "street_view_sample_count": 0,
            "street_view_covered_samples": 0,
            "street_view_visual_summary": "Street View analysis unavailable without a Google Maps API key.",
            "street_view_samples": [],
            "route_analysis_source": "mock",
        }

    def _mock_route_context(
        self,
        source_lat: float,
        source_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> Dict[str, Any]:
        midpoint = ((source_lat + destination_lat) / 2, (source_lon + destination_lon) / 2)
        distance_km = self._haversine_km(source_lat, source_lon, destination_lat, destination_lon)
        data = self._mock_context(midpoint[0], midpoint[1])
        data.update(
            {
                "route_source_latitude": source_lat,
                "route_source_longitude": source_lon,
                "route_destination_latitude": destination_lat,
                "route_destination_longitude": destination_lon,
                "route_distance_km": round(distance_km, 2),
                "route_duration_min": None,
                "route_analysis_source": "mock",
                "street_view_sample_count": 0,
                "street_view_visual_summary": "Route Street View analysis unavailable without a Google Maps API key.",
            }
        )
        return data

    def _linear_route_points(
        self,
        source_lat: float,
        source_lon: float,
        destination_lat: float,
        destination_lon: float,
    ) -> List[Coord]:
        points: List[Coord] = []
        for index in range(MAX_ROUTE_SAMPLES):
            t = index / max(1, MAX_ROUTE_SAMPLES - 1)
            points.append(
                (
                    source_lat + (destination_lat - source_lat) * t,
                    source_lon + (destination_lon - source_lon) * t,
                )
            )
        return points

    def _sample_points(self, points: List[Coord], max_samples: int) -> List[Coord]:
        if not points:
            return []
        if len(points) <= max_samples:
            return points
        return [
            points[round(index * (len(points) - 1) / (max_samples - 1))]
            for index in range(max_samples)
        ]

    def _neighbor_for_heading(self, points: List[Coord], index: int) -> Optional[Coord]:
        if len(points) < 2:
            return None
        if index < len(points) - 1:
            return points[index + 1]
        return points[index - 1]

    def _decode_polyline(self, encoded: str) -> List[Coord]:
        points: List[Coord] = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
            result = 0
            shift = 0
            while True:
                value = ord(encoded[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            lat += ~(result >> 1) if result & 1 else result >> 1

            result = 0
            shift = 0
            while True:
                value = ord(encoded[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            lng += ~(result >> 1) if result & 1 else result >> 1

            points.append((lat / 1e5, lng / 1e5))

        return points

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _bearing_degrees(self, start: Coord, end: Coord) -> float:
        lat1 = math.radians(start[0])
        lat2 = math.radians(end[0])
        dlon = math.radians(end[1] - start[1])
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360
