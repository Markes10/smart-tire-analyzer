# Smart Tire Analyzer — API Reference

> **Base URL:** `http://localhost:8000` (development) · `https://your-domain.com` (production)

---

## Authentication

Currently the API is open (no authentication). For production, add an `Authorization: Bearer <token>` header. The server returns:
- `401 Unauthorized` — Invalid or missing token
- `429 Too Many Requests` — Rate limit exceeded (60 requests/min/IP via Nginx)

---

## Endpoints

### `POST /analyze`

Analyze a tire image. Core inference endpoint.

**Request** — `multipart/form-data`

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `image` | file | ✅ | JPEG/PNG, ≤ 10MB | Tire tread photograph |
| `latitude` | float | ❌ | -90 to 90 | GPS latitude |
| `longitude` | float | ❌ | -180 to 180 | GPS longitude |
| `source_latitude` | float | ❌ | -90 to 90 | Route source latitude |
| `source_longitude` | float | ❌ | -180 to 180 | Route source longitude |
| `destination_latitude` | float | ❌ | -90 to 90 | Route destination latitude |
| `destination_longitude` | float | ❌ | -180 to 180 | Route destination longitude |
| `tire_brand` | string | ❌ | max 100 chars | e.g. "Michelin" |
| `tire_model` | string | ❌ | max 100 chars | e.g. "Pilot Sport 4" |
| `tire_size` | string | ❌ | e.g. "185/65 R15" | ISO tire size |
| `mileage_km` | float | ❌ | ≥ 0 | Current vehicle mileage |
| `vehicle_type` | string | ❌ | — | e.g. "passenger_car" |

**Response `200 OK`**

```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "risk_level": "MODERATE",
  "status": "WARNING — Approaching replacement threshold",
  "replace_immediately": false,
  "confidence": 0.82,
  "predictions": {
    "tread_depths_mm": {
      "tread_1": 3.8,
      "tread_2": 3.5,
      "tread_3": 3.2,
      "tread_4": 3.6,
      "average": 3.52,
      "min": 3.2,
      "max": 3.8
    },
    "health_score": 5.8,
    "remaining_life_km": 18500,
    "wear_pattern": {
      "class_id": 1,
      "label": "edge_wear",
      "cause": "Underinflation",
      "severity": "moderate",
      "confidence": 0.87,
      "probabilities": {
        "center_wear": 0.04,
        "edge_wear": 0.87,
        "uniform_wear": 0.05
      }
    }
  },
  "context": {
    "terrain_type": "urban",
    "road_condition": "wet",
    "road_condition_basis": "Street View visual texture showed mixed or rough surfaces.",
    "route_distance_km": 18.4,
    "route_analysis_source": "google_directions",
    "street_view_available": true,
    "street_view_visual_summary": "Street View coverage 4/5; visual road texture signals: smooth: 3, mixed: 1.",
    "weather_condition": "Rain",
    "temperature_c": 18.5,
    "humidity_pct": 85,
    "visibility_km": 6.2,
    "rain_detected": true
  },
  "reasoning": {
    "source": "gemini",
    "risk_level": "MODERATE",
    "driving_advice": "Increase tire pressure to spec (check placard). Allow extra stopping distance in current wet conditions.",
    "replacement_recommended": false,
    "replacement_urgency": "within_5000km",
    "primary_cause": "Underinflation",
    "additional_notes": "Schedule pressure check within 24 hours."
  },
  "alerts": [
    {
      "level": "MODERATE",
      "message": "Edge wear detected. Check tire pressure immediately."
    }
  ],
  "model_version": "1.2.0",
  "processing_time_ms": 342
}
```

**Error Responses**

| Code | Reason | Notes |
|---|---|---|
| `400` | Bad Request | Missing required fields |
| `413` | Image Too Large | Must be ≤ 10MB |
| `422` | Validation Error | Blurry image / invalid format |
| `500` | Server Error | Internal processing error |

---

### `POST /feedback`

Submit a correction to improve the self-correcting learning model.

**Request Body** — `application/json`

```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "feedback_type": "wrong",
  "corrected_tread_depth_mm": 4.5,
  "corrected_wear_pattern": "uniform_wear",
  "corrected_health_score": 7.2,
  "comment": "Actual tread was measured at 4.5mm with gauge",
  "original_prediction": {}
}
```

| Field | Type | Required | Values |
|---|---|---|---|
| `session_id` | string | ✅ | UUID |
| `feedback_type` | string | ✅ | `wrong`, `inaccurate`, `correct`, `partial` |
| `corrected_tread_depth_mm` | float | ❌ | 0.0 – 12.0 |
| `corrected_wear_pattern` | string | ❌ | See wear pattern classes |
| `corrected_health_score` | float | ❌ | 0.0 – 10.0 |
| `comment` | string | ❌ | Max 500 chars |

**Response `200 OK`**

```json
{
  "feedback_id": "fb_abc123",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "stored": true,
  "retrain_triggered": false,
  "message": "Feedback stored. 12 of 50 corrections collected before next retrain."
}
```

---

### `GET /history`

Retrieve paginated analysis history.

**Query Parameters**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Results per page (max 100) |
| `risk_level` | string | — | Filter: `CRITICAL`, `HIGH`, `MODERATE`, `LOW` |
| `wear_pattern` | string | — | Filter by wear pattern label |
| `start_date` | string | — | ISO 8601 date filter |
| `end_date` | string | — | ISO 8601 date filter |

**Response `200 OK`**

```json
{
  "page": 1,
  "page_size": 20,
  "total": 87,
  "results": [
    {
      "session_id": "uuid",
      "timestamp": "2026-04-09T12:00:00Z",
      "risk_level": "HIGH",
      "health_score": 4.8,
      "avg_tread_mm": 3.1,
      "remaining_life_km": 11200,
      "wear_pattern": "edge_wear"
    }
  ]
}
```

### `GET /history/{session_id}`

Retrieve a single session's full report.

**Response:** Same schema as `POST /analyze` response.

**Error:** `404 Not Found` if session does not exist.

---

### `GET /health`

System health check. Used by load balancer and monitoring.

**Response `200 OK` (healthy)**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "02:15:44",
  "components": {
    "ai_model": "healthy",
    "database": "healthy",
    "api": "healthy",
    "gemini": "available",
    "maps": "available",
    "weather": "available"
  },
  "model_version": "1.2.0"
}
```

**Response `503 Service Unavailable` (degraded)** — Returned if AI model fails to load.

---

## Wear Pattern Classes

| Class ID | Label | Primary Cause |
|---|---|---|
| 0 | `center_wear` | Overinflation |
| 1 | `edge_wear` | Underinflation |
| 2 | `patchy_wear` | Misalignment / imbalance |
| 3 | `uniform_wear` | Normal wear |
| 4 | `one_side_wear` | Camber / alignment issue |
| 5 | `cupping_wear` | Suspension problem |

---

## Risk Levels

| Level | Health Score | Avg Tread | Action |
|---|---|---|---|
| `LOW` | 7.0 – 10.0 | > 5.0mm | Normal monitoring |
| `MODERATE` | 5.0 – 7.0 | 3.0 – 5.0mm | Plan replacement |
| `HIGH` | 3.0 – 5.0 | 1.6 – 3.0mm | Replace within 1,000 km |
| `CRITICAL` | 0.0 – 3.0 | < 1.6mm | Replace immediately |

---

## Tread Safety Thresholds

| Threshold | Value | Notes |
|---|---|---|
| Legal minimum (most regions) | **1.6mm** | Below this = illegal to drive |
| Recommended replacement | **3.0mm** | Industry standard |
| Good / safe | **5.0mm+** | Comfortable safety margin |
| New tire typical depth | **8.0mm** | |

---

## Rate Limits

- **60 requests/minute** per IP address (enforced by Nginx)
- `/health` endpoint: no rate limit
- Max image size: **10MB**
- Max inference timeout: **60 seconds**

---

## Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error description",
  "error_code": "BLUR_DETECTION_FAILED",
  "session_id": null
}
```
