import io
import os
import uuid
from locust import HttpUser, task, between, events
from PIL import Image
import numpy as np


TEST_EMAIL = os.getenv("TEST_EMAIL", "loadtest@smarttire.example")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "LoadTest1")
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")


def make_test_jpeg(width: int = 224, height: int = 224) -> bytes:
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    img_array[:, :] = [50, 50, 50]
    for i in range(0, width, 20):
        img_array[:, i : i + 8] = [30, 30, 30]
    img = Image.fromarray(img_array)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class TireAnalysisUser(HttpUser):
    wait_time = between(1.0, 3.0)
    host = f"http://{API_HOST}:{API_PORT}"

    def on_start(self):
        self.token = None
        self.session_ids = []
        self._ensure_authenticated()

    def _auth_header(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _ensure_authenticated(self):
        resp = self.client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["token"]
            return

        resp = self.client.post(
            "/auth/signup",
            json={
                "first_name": "Load",
                "last_name": "Tester",
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )
        if resp.status_code == 201:
            data = resp.json()
            self.token = data["token"]
        else:
            print(f"Auth setup failed ({resp.status_code}): {resp.text}")

    @task(1)
    def check_health(self):
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health",
        ) as resp:
            if resp.status_code not in (200, 503):
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(3)
    def analyze_tire(self):
        image_bytes = make_test_jpeg()
        files = {"image": ("test_tire.jpg", image_bytes, "image/jpeg")}
        with self.client.post(
            "/analyze",
            files=files,
            headers=self._auth_header(),
            catch_response=True,
            name="/analyze",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                sid = data.get("session_id")
                if sid:
                    self.session_ids.append(sid)
                    if len(self.session_ids) > 100:
                        self.session_ids.pop(0)
            elif resp.status_code in (413, 422, 503):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def get_history(self):
        with self.client.get(
            "/history",
            params={"page": 1, "page_size": 20},
            headers=self._auth_header(),
            catch_response=True,
            name="/history",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "results" not in data or "total" not in data:
                    resp.failure("Missing pagination fields")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def submit_feedback(self):
        if not self.session_ids:
            return
        session_id = np.random.choice(self.session_ids)
        feedback_type = np.random.choice(["wrong", "inaccurate", "correct", "partial"])
        payload = {
            "session_id": session_id,
            "feedback_type": feedback_type,
            "corrected_tread_depth_mm": round(np.random.uniform(1.6, 8.0), 1),
            "comment": f"Load test feedback for {session_id}",
        }
        with self.client.post(
            "/feedback",
            json=payload,
            headers=self._auth_header(),
            catch_response=True,
            name="/feedback",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if not data.get("stored"):
                    resp.failure("Feedback not stored")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def view_dashboard(self):
        with self.client.get(
            "/enterprise/dashboard",
            headers=self._auth_header(),
            catch_response=True,
            name="/enterprise/dashboard",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status: {resp.status_code}")
