# Smart Tire Analyzer API Documentation

Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`  
Prometheus metrics: `http://localhost:8000/metrics`

## Authentication

When `AUTH_ENABLED=true`, protected routes accept either:

- `Authorization: Bearer <jwt-token>` from `GET /enterprise/security/demo-token`
- `X-API-Key: <API_KEY>` when `API_KEY` is set in `.env`

Public routes: `/`, `/health`, `/metrics`, `/docs`, `/openapi.json`

## POST /analyze

Upload a tire image and receive a full analysis report.

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Accept: application/json" \
  -F "image=@./dataset/images/sample_tire.jpg" \
  -F "latitude=28.6139" \
  -F "longitude=77.2090" \
  -F "tire_brand=Michelin" \
  -F "mileage_km=42000"
```

With API key auth:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "X-API-Key: your-secret-key" \
  -F "image=@./dataset/images/sample_tire.jpg"
```

### Response fields (summary)

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique analysis identifier |
| `risk_level` | string | `LOW`, `MODERATE`, `HIGH`, or `CRITICAL` |
| `predictions.tread_depths_mm` | object | T1–T4 depths plus average/min/max |
| `predictions.health_score` | number | 0–10 health score |
| `predictions.remaining_life_km` | number | Estimated remaining tire life |
| `predictions.wear_pattern` | object | Wear class, severity, confidence |
| `reasoning` | object | LLM-generated driving advice |
| `alerts` | array | Safety alerts for the technician |

## POST /feedback

Submit a correction for continuous learning.

```bash
curl -X POST "http://localhost:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "feedback_type": "wrong",
    "corrected_tread_depth_mm": 4.5,
    "corrected_wear_pattern": "edge_wear"
  }'
```

## GET /history

```bash
curl "http://localhost:8000/history?page=1&page_size=20&risk_level=HIGH"
```

## GET /registry

Returns the active model registry snapshot for admin tooling.

```bash
curl "http://localhost:8000/registry"
```

## GET /metrics

Prometheus scrape endpoint.

```bash
curl "http://localhost:8000/metrics"
```

Example series:

- `smart_tire_analyze_requests_total{status="success"}`
- `smart_tire_analyze_latency_seconds_bucket`
- `smart_tire_model_ready`

## GET /health

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/health/ready"
```
