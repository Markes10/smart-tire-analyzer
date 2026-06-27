# Testing Strategy — Smart Tire Analyzer

## 1. Test Pyramid

```
         ╱╲
        ╱ E2E ╲
       ╱═══════╲
      ╱Integration╲
     ╱═════════════╲
    ╱   Unit Tests   ╲
   ╱═══════════════════╲
  ╱ Static Analysis + Lint ╲
 ╱═══════════════════════════╲
```

## 2. Test Categories

### 2.1 Static Analysis
- **Tool**: Ruff (Python), ESLint (JS/TS)
- **What**: Code style, import sorting, unused variables
- **Run**: `ruff check backend/` or `npm run lint`

### 2.2 Unit Tests (16 files, 2000+ lines)

| Test File | What It Tests | Framework |
|---|---|---|
| `test_api.py` | API route behavior, auth scenarios | pytest + httpx |
| `test_class_schemas.py` | Pydantic model validation | pytest |
| `test_enterprise_ai.py` | Enterprise AI extensions | pytest |
| `test_feedback_continuous_learning.py` | Feedback pipeline end-to-end | pytest |
| `test_hybrid_torch.py` | Model forward pass, shape correctness | pytest |
| `test_inference_service_runtime.py` | Mock model inference flow | pytest |
| `test_infrastructure.py` | Directory structure, file existence | pytest |
| `test_integration.py` | Full analysis pipeline | pytest |
| `test_mapillary_service.py` | Mapillary API integration | pytest |
| `test_prepare_dataset.py` | Dataset preparation | pytest |
| `test_preprocessing.py` | Image preprocessing pipeline | pytest |
| `test_route_road_context.py` | Route road condition analysis | pytest |
| `test_sidewall_gemini_client.py` | Sidewall OCR + Gemini client | pytest |
| `test_tire_report.py` | Report building logic | pytest |
| `test_tread_classification_metrics.py` | Wear pattern classification metrics | pytest |

### 2.3 How to Run

```bash
# All tests
python scripts/run_tests.py

# Specific test file
pytest tests/test_api.py -v

# With coverage
pytest --cov=backend/app --cov-report=term-missing

# Parallel execution
pytest -n auto
```

### 2.4 CI/CD Integration

GitHub Actions workflow (`.github/workflows/`):
- On push/PR to `main`
- Run lint → type-check → test
- Build Docker images
- Push to registry

---

## 3. Test Data

- **Sample tire images**: `dataset/images/` (excluded from Git, use DVC or manual copy)
- **Mock API responses**: Located in individual test files as dictionaries
- **Database**: Each test creates an in-memory SQLite database via `ensure_database_ready(force=True)`

---

## 4. Mocking Strategy

| External Dependency | Mocking Approach |
|---|---|
| Gemini AI | `unittest.mock.patch` on `GeminiService.reason` |
| Google Maps | Mock `MapsService.get_road_context` returning fixture data |
| OpenWeather | Mock `WeatherService.get_weather` returning fixture data |
| Mapillary | Mock `MapillaryService.get_road_imagery` |
| ML Model | Use `InferenceService` with `_load_error` for offline mode |
| SQLite Database | Use `ensure_database_ready()` which creates tables in-memory |

---

## 5. Coverage Goals

| Category | Target | Current |
|---|---|---|
| Backend API routes | 90% | ~75% |
| Services | 85% | ~70% |
| Database CRUD | 80% | ~65% |
| AI Model | 70% | ~55% |
| Frontend | 60% | ~30% |
| Overall | 80% | ~65% |

---

## 6. Missing Tests (To Be Added)

1. **Auth rate limiting tests**: Verify 429 after threshold
2. **Input sanitization tests**: SQL injection, XSS payloads
3. **Concurrent request tests**: Race conditions in db sessions
4. **Model version rollback tests**: Registry acceptance/rejection logic
5. **Notification tests**: Email, Slack, webhook delivery
6. **Android UI tests**: Jetpack Compose screenshot tests
7. **Frontend E2E tests**: Cypress or Playwright
