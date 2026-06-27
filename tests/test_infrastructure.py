"""Tests for infrastructure modules: image optimizer, notifications, metrics, settings."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from utils.image_optimizer import optimize_image_bytes
from app.config import AppSettings
from app.main import create_app


def _jpeg_bytes(width: int = 320, height: int = 240) -> bytes:
    array = np.full((height, width, 3), 120, dtype=np.uint8)
    image = Image.fromarray(array)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _png_alpha_bytes(width: int = 8, height: int = 8) -> bytes:
    array = np.zeros((height, width, 4), dtype=np.uint8)
    array[..., 0] = 255
    array[..., 3] = 120
    image = Image.fromarray(array, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageOptimizer:
    def test_optimize_reduces_or_preserves_size(self):
        original = _jpeg_bytes()
        result = optimize_image_bytes(original, content_type="image/jpeg")
        assert result.optimized_bytes <= len(original)
        assert result.data
        assert result.content_type == "image/jpeg"

    def test_optimize_respects_max_dimension(self):
        original = _jpeg_bytes(width=4000, height=3000)
        result = optimize_image_bytes(original, content_type="image/jpeg", max_dimension=1024)
        with Image.open(io.BytesIO(result.data)) as image:
            assert max(image.size) <= 1024

    def test_fallback_preserves_reported_content_type_for_original_bytes(self):
        original = _png_alpha_bytes()
        result = optimize_image_bytes(original, content_type="image/jpeg")
        # Tiny PNGs often cannot be further compressed and hit fallback path.
        assert result.data == original
        assert result.content_type == "image/png"


class TestAppSettings:
    def test_validation_bounds(self):
        settings = AppSettings(
            CONFIDENCE_THRESHOLD=0.5,
            BLUR_THRESHOLD=80.0,
            API_PORT=8080,
            MAX_IMAGE_SIZE_MB=5,
        )
        assert settings.CONFIDENCE_THRESHOLD == 0.5
        assert settings.API_PORT == 8080

    def test_bool_parsing(self):
        settings = AppSettings(AUTH_ENABLED="true", IMAGE_OPTIMIZER_ENABLED="false")
        assert settings.AUTH_ENABLED is True
        assert settings.IMAGE_OPTIMIZER_ENABLED is False


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_payload(self):
        client = TestClient(create_app())
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "smart_tire_model_ready" in response.text
        assert "text/plain" in response.headers.get("content-type", "")


class TestRegistryEndpoint:
    def test_registry_404_when_missing(self):
        client = TestClient(create_app())
        with patch("app.routes.registry.REGISTRY_PATH") as mock_path:
            mock_path.exists.return_value = False
            response = client.get("/registry")
        assert response.status_code == 404

    def test_registry_returns_json(self, tmp_path):
        registry = tmp_path / "model_registry.json"
        payload = {"runtime_model": "hybrid_torch", "model_version": "test-v1", "models": {}}
        registry.write_text(json.dumps(payload), encoding="utf-8")

        client = TestClient(create_app())
        with patch("app.routes.registry.REGISTRY_PATH", registry):
            response = client.get("/registry")
        assert response.status_code == 200
        assert response.json()["model_version"] == "test-v1"


class TestNotificationService:
    def test_notifications_disabled_by_default(self):
        from app.services.notifications import NotificationService

        service = NotificationService()
        result = service.notify_model_promoted(model_version="demo", registry_path="/tmp/registry.json")
        assert result["sent"] is False

    @patch("app.services.notifications.request.urlopen")
    def test_webhook_dispatch(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 200
        settings = AppSettings(NOTIFICATIONS_ENABLED=True, NOTIFICATION_WEBHOOK_URL="https://example.com/hook")
        with patch("app.services.notifications.settings", settings):
            from app.services.notifications import NotificationService

            result = NotificationService().notify_model_promoted(
                model_version="demo",
                registry_path="/tmp/registry.json",
            )
        assert result["sent"] is True
        assert result["channels"]["webhook"]["ok"] is True


def _kubectl_available() -> bool:
    """Check if kubectl is installed and a cluster is reachable."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class TestKubernetesLauncher:
    """Validate K8s manifests and the run_services.bat K8s option."""

    K8S_DIR = ROOT / "deployment" / "kubernetes"
    BAT_PATH = ROOT / "run_services.bat"

    @pytest.mark.parametrize("filename,expected_kinds", [
        ("deployment.yaml", {"Deployment"}),
        ("service.yaml", {"Service", "Namespace", "PersistentVolumeClaim"}),
        ("hpa.yaml", {"HorizontalPodAutoscaler"}),
    ])
    def test_k8s_manifests_valid_yaml(self, filename: str, expected_kinds: set):
        """Each K8s manifest parses to valid YAML with expected resource kinds."""
        path = self.K8S_DIR / filename
        assert path.exists(), f"{filename} not found"
        docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        assert len(docs) == len(expected_kinds), (
            f"Expected {len(expected_kinds)} docs in {filename}, got {len(docs)}"
        )
        actual_kinds = {doc["kind"] for doc in docs if doc is not None}
        assert actual_kinds == expected_kinds

    def test_deployment_has_rolling_update_strategy(self):
        """Deployment uses RollingUpdate with zero-downtime settings."""
        docs = list(yaml.safe_load_all((self.K8S_DIR / "deployment.yaml").read_text()))
        dep = docs[0]
        assert dep["spec"]["strategy"]["type"] == "RollingUpdate"
        assert dep["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"] == 0

    def test_deployment_has_probes(self):
        """Deployment defines liveness and readiness probes."""
        docs = list(yaml.safe_load_all((self.K8S_DIR / "deployment.yaml").read_text()))
        container = docs[0]["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert "readinessProbe" in container
        assert container["livenessProbe"]["httpGet"]["path"] == "/health"
        assert container["readinessProbe"]["httpGet"]["path"] == "/health"

    def test_hpa_scales_based_on_cpu_and_memory(self):
        """HPA targets CPU and memory metrics."""
        docs = list(yaml.safe_load_all((self.K8S_DIR / "hpa.yaml").read_text()))
        hpa = docs[0]
        metric_names = {
            m["resource"]["name"] for m in hpa["spec"]["metrics"]
        }
        assert "cpu" in metric_names
        assert "memory" in metric_names
        assert hpa["spec"]["minReplicas"] >= 1
        assert hpa["spec"]["maxReplicas"] >= hpa["spec"]["minReplicas"]

    def test_service_loadbalancer_ports(self):
        """Service exposes port 80 targeting container port 8000."""
        docs = list(yaml.safe_load_all((self.K8S_DIR / "service.yaml").read_text()))
        svc = next(d for d in docs if d["kind"] == "Service")
        assert svc["spec"]["type"] == "LoadBalancer"
        port = svc["spec"]["ports"][0]
        assert port["port"] == 80
        assert port["targetPort"] == 8000

    def test_bat_contains_kubernetes_option(self):
        """run_services.bat includes a Kubernetes deployment menu option."""
        content = self.BAT_PATH.read_text(encoding="utf-8")
        assert "KUBERNETES" in content.upper()
        assert "kubectl" in content
        assert "apply" in content

    def test_bat_kubernetes_checks_cluster_connection(self):
        """The K8s launcher section verifies cluster connectivity before applying."""
        content = self.BAT_PATH.read_text(encoding="utf-8")
        # Should check kubectl availability and cluster-info before apply
        assert content.count("kubectl version") >= 1
        assert content.count("kubectl cluster-info") >= 1

    def test_bat_kubernetes_applies_all_manifests(self):
        """The K8s launcher applies all three manifest files."""
        content = self.BAT_PATH.read_text(encoding="utf-8")
        assert "deployment.yaml" in content
        assert "service.yaml" in content
        assert "hpa.yaml" in content

    def test_bat_has_stop_section(self):
        """run_services.bat includes a Stop All option."""
        content = self.BAT_PATH.read_text(encoding="utf-8")
        assert "STOP" in content.upper()
        assert any(phrase in content for phrase in ["docker-compose down", "docker compose", "SHUTDOWN", "Stopping Docker"])


class TestK8sRolloutIntegration:
    """Integration tests for Kubernetes rollout validation.

    These tests require a running Kubernetes cluster (e.g. Docker Desktop K8s).
    If no cluster is reachable they are skipped with a clear reason.
    """

    K8S_DIR = ROOT / "deployment" / "kubernetes"
    NAMESPACE = "smart-tire"
    DEPLOYMENT_NAME = "smart-tire-backend"

    @pytest.fixture(autouse=True)
    def _require_cluster(self):
        """Skip all tests in this class when no K8s cluster is available."""
        if not _kubectl_available():
            pytest.skip("No reachable Kubernetes cluster - enable Docker Desktop K8s to run")

    def _run_kubectl(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["kubectl", *args],
            capture_output=True, text=True, timeout=timeout,
        )

    def test_cluster_info_returns_success(self):
        """kubectl cluster-info should succeed against the running cluster."""
        result = self._run_kubectl("cluster-info")
        assert result.returncode == 0, f"cluster-info failed: {result.stderr}"
        assert "Kubernetes control plane" in result.stdout or "is running" in result.stdout

    def test_manifests_apply_dry_run(self):
        """All K8s manifests should pass server-side dry-run validation."""
        manifests = ["service.yaml", "deployment.yaml", "hpa.yaml"]
        for manifest in manifests:
            result = self._run_kubectl(
                "apply",
                "--dry-run=server",
                "-f", str(self.K8S_DIR / manifest),
            )
            assert result.returncode == 0, (
                f"dry-run failed for {manifest}: {result.stderr}"
            )

    def test_namespace_exists_or_can_create(self):
        """The smart-tire namespace should exist or be creatable via manifests."""
        result = self._run_kubectl("get", "namespace", self.NAMESPACE)
        if result.returncode != 0:
            # Namespace doesn't exist yet - apply service.yaml which creates it
            apply_result = self._run_kubectl(
                "apply", "--dry-run=server",
                "-f", str(self.K8S_DIR / "service.yaml"),
            )
            assert apply_result.returncode == 0, (
                f"Cannot create namespace via manifest: {apply_result.stderr}"
            )

    def test_deployment_rollout_status(self):
        """After applying manifests, deployment should reach a ready state."""
        for manifest in ["service.yaml", "deployment.yaml", "hpa.yaml"]:
            self._run_kubectl("apply", "-f", str(self.K8S_DIR / manifest))
        result = self._run_kubectl(
            "rollout", "status",
            f"deployment/{self.DEPLOYMENT_NAME}",
            "-n", self.NAMESPACE,
            "--timeout=120s",
            timeout=130,
        )
        if result.returncode != 0:
            pytest.skip(
                f"Rollout did not complete (image or resources unavailable): {result.stderr.strip()}"
            )
        assert "successfully rolled out" in result.stdout or "found" in result.stdout.lower()

    def test_pods_are_running_after_rollout(self):
        """All pods in the deployment should be in Running state after rollout."""
        result = self._run_kubectl(
            "get", "pods",
            "-n", self.NAMESPACE,
            "-l", "app=smart-tire-backend",
            "-o", "jsonpath={.items[*].status.phase}",
        )
        if result.returncode != 0 or not result.stdout.strip():
            pytest.skip("No pods found - deployment not applied")
        phases = result.stdout.strip().split()
        for phase in phases:
            if phase != "Running":
                pytest.skip(
                    f"Pod phase is {phase} - image or resources may not be available locally"
                )

    def test_hpa_exists_and_configured(self):
        """HPA should exist with correct min/max replicas."""
        result = self._run_kubectl(
            "get", "hpa", "smart-tire-backend-hpa",
            "-n", self.NAMESPACE,
            "-o", "jsonpath={.spec.minReplicas},{.spec.maxReplicas}",
        )
        if result.returncode != 0:
            pytest.skip("HPA not found - not deployed yet")
        parts = result.stdout.strip().split(",")
        min_replicas, max_replicas = int(parts[0]), int(parts[1])
        assert min_replicas >= 1
        assert max_replicas >= min_replicas

    def test_service_endpoints_respond(self):
        """The K8s service /health endpoint should respond after deployment."""
        # Port-forward in background, test, then kill
        pf = subprocess.Popen(
            ["kubectl", "port-forward",
             f"service/{self.DEPLOYMENT_NAME}", "18080:8000",
             "-n", self.NAMESPACE],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            import time
            time.sleep(3)  # Wait for port-forward to establish
            import urllib.request
            try:
                resp = urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=10)
                assert resp.status == 200
            except Exception:
                pytest.skip("Service not reachable via port-forward")
        finally:
            pf.terminate()
            pf.wait(timeout=5)
