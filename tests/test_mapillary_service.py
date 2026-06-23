"""
Unit tests for MapillaryService — mock mode, classification helpers,
API methods with mocked aiohttp, and full flow integration.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.mapillary_service import MapillaryService

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Mock mode (no access token)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMockMode:
    """When MapillaryService has no access token, it returns mock data."""

    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token=None)

    @pytest.mark.asyncio
    async def test_get_road_context_returns_mock_when_disabled(self, svc: MapillaryService):
        result = await svc.get_road_context(48.8566, 2.3522)

        assert result["route_analysis_source"] == "mock"
        assert result["street_view_available"] is False
        assert result["street_view_sample_count"] == 0
        assert result["street_view_covered_samples"] == 0
        assert result["latitude"] == 48.8566
        assert result["longitude"] == 2.3522
        assert result["road_condition"] == "good"
        assert result["terrain_type"] == "flat_urban"

    @pytest.mark.asyncio
    async def test_get_route_road_context_returns_mock_when_disabled(self, svc: MapillaryService):
        result = await svc.get_route_road_context(
            48.8566, 2.3522,
            48.8588, 2.3468,
        )

        assert result["route_analysis_source"] == "mock"
        assert result["route_source_latitude"] == pytest.approx(48.8566)
        assert result["route_destination_longitude"] == pytest.approx(2.3468)
        assert result["route_distance_km"] > 0
        assert result["street_view_available"] is False
        assert "Mapillary" in result["street_view_visual_summary"]

    @pytest.mark.asyncio
    async def test_mock_context_has_expected_keys(self, svc: MapillaryService):
        result = await svc.get_road_context(40.7128, -74.0060)

        expected_keys = {
            "terrain_type", "road_condition", "road_condition_basis",
            "elevation_m", "latitude", "longitude",
            "street_view_available", "street_view_sample_count",
            "street_view_covered_samples", "street_view_visual_summary",
            "street_view_samples", "route_analysis_source",
            "base_road_wear_multiplier", "road_wear_multiplier",
            "terrain_wear_multiplier", "traffic_density",
            "traffic_multiplier", "traffic_method",
            "is_peak_hour", "legacy_terrain_type",
        }
        assert expected_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_mock_route_context_has_route_keys(self, svc: MapillaryService):
        result = await svc.get_route_road_context(40.7128, -74.0060, 40.7580, -73.9855)

        extra_keys = {
            "route_source_latitude", "route_source_longitude",
            "route_destination_latitude", "route_destination_longitude",
            "route_distance_km", "route_duration_min",
        }
        assert extra_keys.issubset(result.keys())
        # ~5.3 km from lower Manhattan to midtown east
        assert result["route_distance_km"] == pytest.approx(5.31, abs=0.2)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Classification helpers (pure functions, no network needed)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTerrainClassification:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_classify_flat(self, svc: MapillaryService):
        assert svc._classify_terrain(10.0) == "flat_urban"
        assert svc._classify_terrain(49.9) == "flat_urban"
        assert svc._classify_terrain(0.0) == "flat_urban"

    def test_classify_rolling(self, svc: MapillaryService):
        assert svc._classify_terrain(50.0) == "rolling_suburban"
        assert svc._classify_terrain(150.0) == "rolling_suburban"
        assert svc._classify_terrain(299.9) == "rolling_suburban"

    def test_classify_hilly(self, svc: MapillaryService):
        assert svc._classify_terrain(300.0) == "hilly"
        assert svc._classify_terrain(500.0) == "hilly"
        assert svc._classify_terrain(799.9) == "hilly"

    def test_classify_mountainous(self, svc: MapillaryService):
        assert svc._classify_terrain(800.0) == "mountainous"
        assert svc._classify_terrain(1500.0) == "mountainous"


class TestRouteTerrainClassification:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_empty_list(self, svc: MapillaryService):
        assert svc._classify_route_terrain([]) == "flat_urban"

    def test_flat_by_average(self, svc: MapillaryService):
        # avg ~10, range ~20
        assert svc._classify_route_terrain([5.0, 10.0, 15.0]) == "flat_urban"

    def test_hilly_by_range(self, svc: MapillaryService):
        # avg ~100, range ~200
        assert svc._classify_route_terrain([10.0, 100.0, 210.0]) == "hilly"

    def test_mountainous_by_range(self, svc: MapillaryService):
        # avg ~300, range ~500
        assert svc._classify_route_terrain([50.0, 300.0, 550.0]) == "mountainous"

    def test_mountainous_by_average(self, svc: MapillaryService):
        # avg ~900, range ~100
        assert svc._classify_route_terrain([850.0, 900.0, 950.0]) == "mountainous"

    def test_proxies_to_classify_terrain(self, svc: MapillaryService):
        # avg ~100, range ~40 — falls through to _classify_terrain
        assert svc._classify_route_terrain([80.0, 100.0, 120.0]) == "rolling_suburban"


class TestRoadConditionEstimation:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def _make_sample(
        self,
        surface_texture: str | None = None,
        has_images: bool = True,
    ) -> dict:
        visual = {"surface_texture": surface_texture} if surface_texture else {}
        return {
            "mapillary_images": [{"id": "img1"}] if has_images else [],
            "visual": visual,
        }

    def test_poor_condition(self, svc: MapillaryService):
        samples = [self._make_sample("rough") for _ in range(4)]
        condition, basis = svc._estimate_road_condition(samples, "flat_urban")
        assert condition == "poor"
        assert "rough" in basis.lower()

    def test_fair_condition_mixed(self, svc: MapillaryService):
        samples = [self._make_sample("mixed"), self._make_sample("mixed")]
        condition, basis = svc._estimate_road_condition(samples, "flat_urban")
        assert condition == "fair"

    def test_fair_condition_hilly(self, svc: MapillaryService):
        samples = [self._make_sample("smooth")]
        condition, basis = svc._estimate_road_condition(samples, "hilly")
        assert condition == "fair"
        assert "terrain" in basis.lower()

    def test_good_condition_with_coverage(self, svc: MapillaryService):
        samples = [self._make_sample("smooth") for _ in range(3)]
        condition, basis = svc._estimate_road_condition(samples, "flat_urban")
        assert condition == "good"
        assert "smooth" in basis.lower()

    def test_good_condition_no_coverage(self, svc: MapillaryService):
        samples = [self._make_sample(has_images=False)]
        condition, basis = svc._estimate_road_condition(samples, "flat_urban")
        assert condition == "good"
        assert "No Mapillary" in basis

    def test_edge_case_no_visuals(self, svc: MapillaryService):
        samples = [{"mapillary_images": [], "visual": None}]
        condition, basis = svc._estimate_road_condition(samples, "flat_urban")
        assert condition == "good"


class TestVisualSummary:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_empty_samples(self, svc: MapillaryService):
        assert "No route samples" in svc._build_visual_summary([])

    def test_no_coverage(self, svc: MapillaryService):
        samples = [{"mapillary_images": [], "visual": None}]
        result = svc._build_visual_summary(samples)
        assert "No Mapillary imagery found" in result

    def test_no_texture(self, svc: MapillaryService):
        samples = [{"mapillary_images": [{"id": "x"}], "visual": {}}]
        result = svc._build_visual_summary(samples)
        assert "texture could not be read" in result

    def test_with_textures(self, svc: MapillaryService):
        samples = [
            {"mapillary_images": [{"id": "a"}], "visual": {"surface_texture": "smooth"}},
            {"mapillary_images": [{"id": "b"}], "visual": {"surface_texture": "rough"}},
        ]
        result = svc._build_visual_summary(samples)
        assert "coverage 2/2" in result
        assert "rough: 1" in result
        assert "smooth: 1" in result


class TestHaversine:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_zero_distance(self, svc: MapillaryService):
        assert svc._haversine_km(48.8566, 2.3522, 48.8566, 2.3522) == 0.0

    def test_known_distance_paris(self, svc: MapillaryService):
        # Eiffel Tower to Arc de Triomphe ~3.3 km
        dist = svc._haversine_km(48.8584, 2.2945, 48.8738, 2.2950)
        assert dist == pytest.approx(1.7, abs=0.3)

    def test_longer_distance(self, svc: MapillaryService):
        # Paris to London ~344 km
        dist = svc._haversine_km(48.8566, 2.3522, 51.5072, -0.1276)
        assert dist == pytest.approx(344, abs=5)

    def test_symmetry(self, svc: MapillaryService):
        a = svc._haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
        b = svc._haversine_km(34.0522, -118.2437, 40.7128, -74.0060)
        assert a == pytest.approx(b)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Helper methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestRouteSampling:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_linear_route_points_count(self, svc: MapillaryService):
        points = svc._linear_route_points(0.0, 0.0, 1.0, 1.0)
        assert len(points) == 5

    def test_linear_route_points_start_end(self, svc: MapillaryService):
        points = svc._linear_route_points(10.0, 20.0, 30.0, 40.0)
        assert points[0] == (10.0, 20.0)
        assert points[-1] == (30.0, 40.0)

    def test_linear_route_points_interpolated(self, svc: MapillaryService):
        points = svc._linear_route_points(0.0, 0.0, 10.0, 10.0)
        assert points[2] == (5.0, 5.0)  # midpoint

    def test_sample_points_empty(self, svc: MapillaryService):
        assert svc._sample_points([], 3) == []

    def test_sample_points_fewer_than_n(self, svc: MapillaryService):
        pts = [(1.0, 1.0), (2.0, 2.0)]
        assert svc._sample_points(pts, 5) == pts

    def test_sample_points_downsample(self, svc: MapillaryService):
        pts = [(i, i) for i in range(10)]
        sampled = svc._sample_points(pts, 3)
        assert len(sampled) == 3


class TestPublicSamples:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def test_empty_input(self, svc: MapillaryService):
        assert svc._public_samples([]) == []

    def test_with_images(self, svc: MapillaryService):
        samples = [
            {
                "latitude": 48.85,
                "longitude": 2.35,
                "elevation_m": 50.0,
                "mapillary_images": [
                    {"id": "img123", "thumb_256_url": "https://thumb.example.com/img.jpg"},
                ],
                "visual": {"surface_texture": "smooth", "edge_density": 0.05, "texture_score": 15.0},
            }
        ]
        result = svc._public_samples(samples)
        assert len(result) == 1
        assert result[0]["latitude"] == 48.85
        assert result[0]["longitude"] == 2.35
        assert result[0]["street_view_status"] == "OK"
        assert result[0]["mapillary_image_id"] == "img123"
        assert result[0]["surface_texture"] == "smooth"

    def test_without_images(self, svc: MapillaryService):
        samples = [
            {
                "latitude": 48.85,
                "longitude": 2.35,
                "elevation_m": None,
                "mapillary_images": [],
                "visual": {},
            }
        ]
        result = svc._public_samples(samples)
        assert result[0]["street_view_status"] == "UNAVAILABLE"
        assert result[0]["mapillary_image_id"] is None
        assert result[0]["mapillary_thumb_url"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. API methods with mocked aiohttp
# ═══════════════════════════════════════════════════════════════════════════════


class TestSearchImages:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_returns_image_list(self, svc: MapillaryService):
        """Successful search returns parsed image results."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp

        async def mock_json():
            return {
                "data": [
                    {
                        "id": "12345",
                        "thumb_256_url": "https://thumb.mapillary.com/256.jpg",
                        "thumb_1024_url": "https://thumb.mapillary.com/1024.jpg",
                        "captured_at": "2025-01-15T10:00:00Z",
                        "compass_angle": 180.0,
                        "altitude": 50.0,
                        "geometry": {"coordinates": [2.3522, 48.8566]},
                    }
                ]
            }
        mock_resp.json = mock_json

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            results = await svc._search_images(48.8566, 2.3522)

        assert len(results) == 1
        assert results[0]["id"] == "12345"
        assert results[0]["latitude"] == 48.8566
        assert results[0]["longitude"] == 2.3522
        assert results[0]["compass_angle"] == 180.0

    @pytest.mark.asyncio
    async def test_returns_empty_on_empty_response(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp

        async def mock_json():
            return {"data": []}
        mock_resp.json = mock_json

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            results = await svc._search_images(48.8566, 2.3522)
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_401(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 401
        mock_resp.__aenter__.return_value = mock_resp

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            results = await svc._search_images(48.8566, 2.3522)
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_429(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 429
        mock_resp.__aenter__.return_value = mock_resp

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            results = await svc._search_images(48.8566, 2.3522)
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, svc: MapillaryService):
        with patch(
            "aiohttp.ClientSession.get",
            side_effect=Exception("Network error"),
        ):
            results = await svc._search_images(48.8566, 2.3522)
        assert results == []


class TestFetchElevation:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_returns_elevation(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp

        async def mock_json():
            return {"results": [{"elevation": 123.45}]}
        mock_resp.json = mock_json

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            elev = await svc._fetch_elevation(48.8566, 2.3522)
        assert elev == pytest.approx(123.45)

    @pytest.mark.asyncio
    async def test_fallback_on_empty_results(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp
        mock_resp.json.return_value = {"results": []}

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            elev = await svc._fetch_elevation(48.8566, 2.3522)
        assert elev == 50.0

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self, svc: MapillaryService):
        with patch(
            "aiohttp.ClientSession.get",
            side_effect=Exception("Timeout"),
        ):
            elev = await svc._fetch_elevation(48.8566, 2.3522)
        assert elev == 50.0


class TestFetchImageBytes:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_downloads_bytes(self, svc: MapillaryService):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp

        async def mock_read():
            return b"image-bytes"
        mock_resp.read = mock_read

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            result = await svc._fetch_image_bytes("https://img.example.com/photo.jpg")
        assert result == b"image-bytes"

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_url(self, svc: MapillaryService):
        result = await svc._fetch_image_bytes("")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_none_url(self, svc: MapillaryService):
        result = await svc._fetch_image_bytes(None)  # type: ignore[arg-type]
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, svc: MapillaryService):
        with patch(
            "aiohttp.ClientSession.get",
            side_effect=Exception("Timeout"),
        ):
            result = await svc._fetch_image_bytes("https://img.example.com/photo.jpg")
        assert result is None


class TestImageSummarize:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService()

    def _make_test_image(self, intensity: int = 128) -> bytes:
        """Create a synthetic grayscale image for testing."""
        arr = np.full((100, 100), intensity, dtype=np.uint8)
        # Add some noise for texture
        arr[40:80, 20:80] = np.random.default_rng(42).integers(
            max(0, intensity - 30), min(255, intensity + 30), (40, 60), dtype=np.uint8
        )
        buf = io.BytesIO()
        Image.fromarray(arr, mode="L").save(buf, format="PNG")
        return buf.getvalue()

    def test_smooth_surface(self, svc: MapillaryService):
        # Low contrast image → smooth
        img_bytes = self._make_test_image(intensity=128)
        result = svc._summarize_image(img_bytes)
        assert result["surface_texture"] == "smooth"
        assert "edge_density" in result
        assert "texture_score" in result
        assert "brightness" in result

    def test_rough_surface(self, svc: MapillaryService):
        # High contrast image → rough
        arr = np.zeros((100, 100), dtype=np.uint8)
        rng = np.random.default_rng(99)
        arr[:, :] = rng.integers(0, 255, (100, 100), dtype=np.uint8)
        buf = io.BytesIO()
        Image.fromarray(arr, mode="L").save(buf, format="PNG")
        img_bytes = buf.getvalue()

        result = svc._summarize_image(img_bytes)
        assert result["surface_texture"] == "rough"



    def test_corrupted_bytes_returns_unknown(self, svc: MapillaryService):
        # Random bytes that PIL cannot decode → error path
        result = svc._summarize_image(b"\\xff\\xd8\\xff\\xe0not-a-valid-jpeg")
        assert result["surface_texture"] == "unknown"
        assert "analysis_error" in result


class TestAnalyzeImageVisual:
    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_url(self, svc: MapillaryService):
        result = await svc._analyze_image_visual({})
        assert result is None

    @pytest.mark.asyncio
    async def test_with_valid_image(self, svc: MapillaryService):
        # Create a valid image
        arr = np.full((100, 100), 128, dtype=np.uint8)
        buf = io.BytesIO()
        Image.fromarray(arr, mode="L").save(buf, format="PNG")
        img_bytes = buf.getvalue()

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp

        async def mock_read():
            return img_bytes
        mock_resp.read = mock_read

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            result = await svc._analyze_image_visual({"thumb_1024_url": "https://img.example.com/photo.jpg"})

        assert result is not None
        assert result["surface_texture"] in ("smooth", "mixed", "rough")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Full flow integration test — mocked API calls end to end
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullFlow:
    """Test the full get_road_context / get_route_road_context with mocked APIs."""

    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_get_road_context_with_data(self, svc: MapillaryService):
        """Full get_road_context flow with mocked image search and elevation."""
        # Mock _search_images
        svc._search_images = AsyncMock(
            return_value=[
                {
                    "id": "img1",
                    "thumb_256_url": "https://img.example.com/256.jpg",
                    "thumb_1024_url": "https://img.example.com/1024.jpg",
                    "captured_at": "2025-01-01T00:00:00Z",
                    "compass_angle": 90.0,
                    "altitude": 100.0,
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                }
            ]
        )
        # Mock _fetch_elevation
        svc._fetch_elevation = AsyncMock(return_value=75.0)
        # Mock _analyze_image_visual
        svc._analyze_image_visual = AsyncMock(
            return_value={
                "surface_texture": "smooth",
                "edge_density": 0.08,
                "texture_score": 18.5,
                "brightness": 110.0,
            }
        )

        result = await svc.get_road_context(48.8566, 2.3522)

        assert result["route_analysis_source"] == "mapillary_single_point"
        assert result["street_view_available"] is True
        assert result["street_view_sample_count"] == 1
        assert result["street_view_covered_samples"] == 1
        assert result["road_condition"] == "good"
        assert result["terrain_type"] == "rolling_suburban"
        assert result["elevation_m"] == 75.0
        assert result["latitude"] == 48.8566

    @pytest.mark.asyncio
    async def test_get_road_context_fallback_on_error(self, svc: MapillaryService):
        """When APIs fail, get_road_context falls back to mock data."""
        svc._search_images = AsyncMock(side_effect=Exception("API error"))

        result = await svc.get_road_context(48.8566, 2.3522)

        assert result["route_analysis_source"] == "mock"
        assert result["street_view_available"] is False

    @pytest.mark.asyncio
    async def test_get_route_road_context_with_data(self, svc: MapillaryService):
        """Full route context flow with mocked samples."""
        svc._linear_route_points = MagicMock(
            return_value=[(48.85, 2.35), (48.86, 2.36), (48.87, 2.37)]
        )
        svc._analyze_route_sample = AsyncMock(
            return_value={
                "latitude": 48.86,
                "longitude": 2.36,
                "elevation_m": 60.0,
                "mapillary_images": [{"id": "img1"}],
                "visual": {"surface_texture": "smooth"},
            }
        )

        result = await svc.get_route_road_context(48.85, 2.35, 48.87, 2.37)

        assert result["route_analysis_source"] == "mapillary_linear"
        assert result["street_view_sample_count"] == 3
        assert result["street_view_covered_samples"] == 3
        assert result["street_view_available"] is True
        assert result["road_condition"] == "good"
        assert result["route_distance_km"] > 0

    @pytest.mark.asyncio
    async def test_get_route_road_context_fallback_on_error(self, svc: MapillaryService):
        svc._linear_route_points = MagicMock(side_effect=Exception("Unexpected error"))

        result = await svc.get_route_road_context(48.85, 2.35, 48.87, 2.37)

        assert result["route_analysis_source"] == "mock"


class TestFullFlowNoImages:
    """Edge case: Mapillary search returns empty — service works with elevation only."""

    @pytest.fixture
    def svc(self) -> MapillaryService:
        return MapillaryService(access_token="MLY|test-token")

    @pytest.mark.asyncio
    async def test_road_context_no_images_found(self, svc: MapillaryService):
        svc._search_images = AsyncMock(return_value=[])
        svc._fetch_elevation = AsyncMock(return_value=30.0)

        result = await svc.get_road_context(48.8566, 2.3522)

        assert result["street_view_available"] is False
        assert result["street_view_covered_samples"] == 0
        assert result["elevation_m"] == 30.0
        # Road condition should still be "good" with default basis
        assert result["road_condition"] == "good"
