"""
Mapillary Service — Street-level road context powered by Mapillary API v4.

Replaces Google Maps Street View with Mapillary's crowd-sourced street imagery.
Uses the Mapillary graph API to find nearby images, fetch thumbnails, and
analyze road surface texture — all with a user-provided access token.

For routing, falls back to linear interpolation (Mapillary has no directions API).
For elevation, uses OpenStreetMap's free elevation service.

Output shape matches MapsService so callers are interchangeable.
"""

from __future__ import annotations

import asyncio
import io
import logging
import math
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

import aiohttp
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

MAPILLARY_GRAPH_URL = "https://graph.mapillary.com"
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
MAX_ROUTE_SAMPLES = 5
SEARCH_RADIUS_M = 30  # Search radius for nearby Mapillary images
MAX_IMAGES_PER_POINT = 3

Coord = Tuple[float, float]


class MapillaryService:
    """
    Street-level road context service backed by Mapillary API v4.

    Features:
    - Search Mapillary images near a GPS coordinate
    - Download thumbnails for visual road-surface texture analysis
    - Elevation data from Open Elevation API
    - Route sampling with linear fallback (no directions API needed)
    """

    def __init__(self, access_token: str | None = None):
        """
        Args:
            access_token: Mapillary client access token (MLY|...).
                          If None, the service returns mock data.
        """
        self.access_token = access_token
        self.enabled = bool(access_token)
        if not self.enabled:
            logger.info("MapillaryService: No access token — using mock road context")

    # ── Public API (matches MapsService interface) ──────────────────────────

    async def get_road_context(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch point-level terrain, road condition, and visual context via Mapillary."""
        if not self.enabled:
            return self._mock_context(lat, lon)

        try:
            elevation_m, images = await asyncio.gather(
                self._fetch_elevation(lat, lon),
                self._search_images(lat, lon),
            )
            terrain_type = self._classify_terrain(elevation_m)

            # Analyze best image for road texture
            visual_summary = None
            street_view_status = "UNAVAILABLE"
            if images:
                best = images[0]
                street_view_status = "OK"
                visual_summary = await self._analyze_image_visual(best)

            sample = {
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation_m,
                "mapillary_images": images,
                "visual": visual_summary,
            }
            road_condition, road_basis = self._estimate_road_condition(
                [sample], terrain_type
            )

            return {
                "terrain_type": terrain_type,
                "road_condition": road_condition,
                "road_condition_basis": road_basis,
                "elevation_m": elevation_m,
                "latitude": lat,
                "longitude": lon,
                "street_view_available": street_view_status == "OK",
                "street_view_sample_count": 1,
                "street_view_covered_samples": 1 if images else 0,
                "street_view_visual_summary": self._build_visual_summary([sample]),
                "street_view_samples": self._public_samples([sample]),
                "route_analysis_source": "mapillary_single_point",
                "base_road_wear_multiplier": 1.0,
                "road_wear_multiplier": 1.0,
                "terrain_wear_multiplier": 1.0,
                "traffic_density": "moderate",
                "traffic_multiplier": 1.0,
                "traffic_method": "default",
                "is_peak_hour": False,
                "legacy_terrain_type": terrain_type,
            }
        except Exception as exc:
            logger.warning("Mapillary road context error: %s — using mock", exc)
            return self._mock_context(lat, lon)

    async def get_route_road_context(
        self,
        source_lat: float,
        source_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> Dict[str, Any]:
        """Analyze road context along a route using Mapillary imagery sampling."""
        if not self.enabled:
            return self._mock_route_context(source_lat, source_lon, dest_lat, dest_lon)

        try:
            route_points = self._linear_route_points(
                source_lat, source_lon, dest_lat, dest_lon
            )
            samples: List[Dict[str, Any]] = []

            for index, (lat, lon) in enumerate(route_points):
                sample = await self._analyze_route_sample(lat, lon, index)
                samples.append(sample)

            elevations = [
                float(s["elevation_m"])
                for s in samples
                if isinstance(s.get("elevation_m"), (int, float))
            ]
            terrain_type = self._classify_route_terrain(elevations)
            road_condition, road_basis = self._estimate_road_condition(
                samples, terrain_type
            )

            midpoint = route_points[len(route_points) // 2]
            elevation_avg = (
                round(sum(elevations) / len(elevations), 2) if elevations else None
            )
            distance_km = self._haversine_km(
                source_lat, source_lon, dest_lat, dest_lon
            )

            return {
                "terrain_type": terrain_type,
                "road_condition": road_condition,
                "road_condition_basis": road_basis,
                "elevation_m": elevation_avg,
                "latitude": midpoint[0],
                "longitude": midpoint[1],
                "route_source_latitude": source_lat,
                "route_source_longitude": source_lon,
                "route_destination_latitude": dest_lat,
                "route_destination_longitude": dest_lon,
                "route_distance_km": round(distance_km, 2),
                "route_duration_min": None,
                "route_analysis_source": "mapillary_linear",
                "street_view_available": any(
                    s.get("mapillary_images") for s in samples
                ),
                "street_view_sample_count": len(samples),
                "street_view_covered_samples": sum(
                    1 for s in samples if s.get("mapillary_images")
                ),
                "street_view_visual_summary": self._build_visual_summary(samples),
                "street_view_samples": self._public_samples(samples),
                "base_road_wear_multiplier": 1.0,
                "road_wear_multiplier": 1.0,
                "terrain_wear_multiplier": 1.0,
                "traffic_density": "moderate",
                "traffic_multiplier": 1.0,
                "traffic_method": "default",
                "is_peak_hour": False,
                "legacy_terrain_type": terrain_type,
            }
        except Exception as exc:
            logger.warning("Mapillary route context error: %s — using mock", exc)
            return self._mock_route_context(source_lat, source_lon, dest_lat, dest_lon)

    # ── Mapillary API calls ─────────────────────────────────────────────────

    async def _search_images(
        self, lat: float, lon: float
    ) -> List[Dict[str, Any]]:
        """Search for Mapillary images near a coordinate using radius search."""
        url = f"{MAPILLARY_GRAPH_URL}/images"
        params = {
            "lat": lat,
            "lng": lon,
            "radius": SEARCH_RADIUS_M,
            "limit": MAX_IMAGES_PER_POINT,
            "fields": "id,thumb_256_url,thumb_1024_url,captured_at,compass_angle,altitude,geometry",
        }
        headers = {"Authorization": f"OAuth {self.access_token}"}

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(
                    url, params=params, headers=headers
                ) as resp:
                    if resp.status == 401:
                        logger.warning("Mapillary: Invalid access token (401)")
                        return []
                    if resp.status == 429:
                        logger.warning("Mapillary: Rate limited (429)")
                        return []
                    resp.raise_for_status()
                    data = await resp.json()

            items = data.get("data", []) if isinstance(data, dict) else []
            results = []
            for item in items:
                geom = item.get("geometry", {})
                coords = geom.get("coordinates", []) if isinstance(geom, dict) else []
                results.append(
                    {
                        "id": item.get("id"),
                        "thumb_256_url": item.get("thumb_256_url"),
                        "thumb_1024_url": item.get("thumb_1024_url"),
                        "captured_at": item.get("captured_at"),
                        "compass_angle": item.get("compass_angle"),
                        "altitude": item.get("altitude"),
                        "longitude": coords[0] if len(coords) > 0 else None,
                        "latitude": coords[1] if len(coords) > 1 else None,
                    }
                )
            return results
        except Exception as exc:
            logger.warning("Mapillary image search error: %s", exc)
            return []

    async def _fetch_image_bytes(self, url: str) -> Optional[bytes]:
        """Download image bytes from a thumbnail URL."""
        if not url:
            return None
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.read()
        except Exception as exc:
            logger.debug("Mapillary thumbnail download error: %s", exc)
            return None

    async def _fetch_elevation(self, lat: float, lon: float) -> float:
        """Fetch elevation from Open Elevation API (free, no key required)."""
        try:
            params = {"locations": f"{lat},{lon}"}
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(
                    OPEN_ELEVATION_URL, params=params
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            results = data.get("results", [])
            if results:
                return float(results[0].get("elevation", 50))
        except Exception as exc:
            logger.debug("Elevation fetch error: %s", exc)
        return 50.0

    # ── Image analysis ──────────────────────────────────────────────────────

    async def _analyze_image_visual(
        self, image_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Download and analyze a Mapillary thumbnail for road texture."""
        # Prefer 1024px, fall back to 256px
        url = image_info.get("thumb_1024_url") or image_info.get("thumb_256_url")
        if not url:
            return None

        image_bytes = await self._fetch_image_bytes(url)
        if not image_bytes:
            return None

        return self._summarize_image(image_bytes)

    def _summarize_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extract road surface texture signals from an image."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                gray = np.asarray(img.convert("L"), dtype=np.float32)
        except Exception as exc:
            return {"surface_texture": "unknown", "analysis_error": str(exc)}

        height = gray.shape[0]
        road_crop = gray[int(height * 0.55):, :]
        if road_crop.size == 0:
            return {"surface_texture": "unknown", "analysis_error": "empty crop"}

        grad_y, grad_x = np.gradient(road_crop)
        magnitude = np.sqrt(grad_x * grad_x + grad_y * grad_y)
        edge_density = float(np.mean(magnitude > 28.0))
        texture_score = float(np.percentile(magnitude, 85))
        brightness = float(np.mean(road_crop))

        if edge_density > 0.22 or texture_score > 42:
            surface = "rough"
        elif edge_density > 0.12 or texture_score > 26:
            surface = "mixed"
        else:
            surface = "smooth"

        return {
            "surface_texture": surface,
            "edge_density": round(edge_density, 4),
            "texture_score": round(texture_score, 2),
            "brightness": round(brightness, 1),
        }

    # ── Route sampling ──────────────────────────────────────────────────────

    async def _analyze_route_sample(
        self, lat: float, lon: float, index: int
    ) -> Dict[str, Any]:
        elevation_m, images = await asyncio.gather(
            self._fetch_elevation(lat, lon),
            self._search_images(lat, lon),
        )
        visual_summary = None
        if images:
            visual_summary = await self._analyze_image_visual(images[0])

        return {
            "latitude": lat,
            "longitude": lon,
            "elevation_m": elevation_m,
            "mapillary_images": images,
            "visual": visual_summary,
        }

    def _linear_route_points(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> List[Coord]:
        points: List[Coord] = []
        for i in range(MAX_ROUTE_SAMPLES):
            t = i / max(1, MAX_ROUTE_SAMPLES - 1)
            points.append(
                (
                    lat1 + (lat2 - lat1) * t,
                    lon1 + (lon2 - lon1) * t,
                )
            )
        return points

    def _sample_points(self, points: List[Coord], n: int) -> List[Coord]:
        if not points:
            return []
        if len(points) <= n:
            return points
        return [
            points[round(i * (len(points) - 1) / (n - 1))] for i in range(n)
        ]

    # ── Classification helpers ──────────────────────────────────────────────

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
        rng = max(values) - min(values)
        if rng > 400 or avg >= 800:
            return "mountainous"
        if rng > 160 or avg >= 300:
            return "hilly"
        return self._classify_terrain(avg)

    def _estimate_road_condition(
        self, samples: List[Dict[str, Any]], terrain_type: str
    ) -> Tuple[str, str]:
        visuals = [
            s.get("visual", {}).get("surface_texture")
            for s in samples
            if isinstance(s.get("visual"), dict)
        ]
        counts = Counter(t for t in visuals if t)
        covered = sum(1 for s in samples if s.get("mapillary_images"))

        if counts.get("rough", 0) >= max(1, math.ceil(max(covered, 1) / 2)):
            return "poor", "Mapillary imagery showed rough road surface on most samples."
        if counts.get("rough", 0) or counts.get("mixed", 0) >= 2:
            return "fair", "Mapillary imagery showed mixed or rough road surfaces."
        if terrain_type in {"hilly", "mountainous"}:
            return "fair", "Route terrain increases tire load."
        if covered > 0:
            return "good", "Mapillary imagery available — surface texture looked smooth."
        return "good", "No Mapillary imagery nearby; using default road condition."

    def _build_visual_summary(self, samples: List[Dict[str, Any]]) -> str:
        total = len(samples)
        covered = sum(1 for s in samples if s.get("mapillary_images"))
        textures = [
            s.get("visual", {}).get("surface_texture")
            for s in samples
            if isinstance(s.get("visual"), dict)
        ]
        counts = Counter(t for t in textures if t)
        if not total:
            return "No route samples analyzed."
        if not covered:
            return f"No Mapillary imagery found near {total} sampled point(s)."
        if not counts:
            return f"Mapillary imagery available for {covered}/{total} points, but texture could not be read."
        parts = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        return f"Mapillary coverage {covered}/{total}; road surface textures: {parts}."

    def _public_samples(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for s in samples:
            visual = s.get("visual", {}) if isinstance(s.get("visual"), dict) else {}
            images = s.get("mapillary_images", [])
            thumb_url = images[0].get("thumb_256_url") if images else None
            result.append(
                {
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                    "elevation_m": s.get("elevation_m"),
                    "street_view_status": "OK" if images else "UNAVAILABLE",
                    "mapillary_image_id": images[0].get("id") if images else None,
                    "mapillary_thumb_url": thumb_url,
                    "surface_texture": visual.get("surface_texture"),
                    "edge_density": visual.get("edge_density"),
                    "texture_score": visual.get("texture_score"),
                }
            )
        return result

    # ── Mock fallback ──────────────────────────────────────────────────────

    def _mock_context(self, lat: float, lon: float) -> Dict[str, Any]:
        return {
            "terrain_type": "flat_urban",
            "road_condition": "good",
            "road_condition_basis": "No Mapillary access token configured; using defaults.",
            "elevation_m": None,
            "latitude": lat,
            "longitude": lon,
            "street_view_available": False,
            "street_view_sample_count": 0,
            "street_view_covered_samples": 0,
            "street_view_visual_summary": "Mapillary analysis unavailable — no access token provided.",
            "street_view_samples": [],
            "route_analysis_source": "mock",
            "base_road_wear_multiplier": 1.0,
            "road_wear_multiplier": 1.0,
            "terrain_wear_multiplier": 1.0,
            "traffic_density": "moderate",
            "traffic_multiplier": 1.0,
            "traffic_method": "default",
            "is_peak_hour": False,
            "legacy_terrain_type": "flat_urban",
        }

    def _mock_route_context(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> Dict[str, Any]:
        midpoint = ((lat1 + lat2) / 2, (lon1 + lon2) / 2)
        distance = self._haversine_km(lat1, lon1, lat2, lon2)
        data = self._mock_context(midpoint[0], midpoint[1])
        data.update(
            {
                "route_source_latitude": lat1,
                "route_source_longitude": lon1,
                "route_destination_latitude": lat2,
                "route_destination_longitude": lon2,
                "route_distance_km": round(distance, 2),
                "route_duration_min": None,
                "route_analysis_source": "mock",
                "street_view_sample_count": 0,
                "street_view_visual_summary": "Route Mapillary analysis unavailable.",
            }
        )
        return data

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
