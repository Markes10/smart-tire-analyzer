# Load Testing — Smart Tire Analyzer API

Locust-based load tests for the backend API.

## Prerequisites

```bash
pip install locust pillow numpy
```

## Quick Start

Start the backend server, then:

```bash
locust -f tests/load_testing/locustfile.py --host=http://localhost:8000
```

Open the Locust web UI at http://localhost:8089 and configure:
- **Number of users** (e.g. 10–50)
- **Spawn rate** (e.g. 5–10 users/sec)
- **Host** (pre-filled)

## Headless mode

```bash
locust -f tests/load_testing/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  -u 20 \
  -r 5 \
  --run-time 5m \
  --html report.html
```

## Environment variables

| Variable    | Default          | Description         |
|-------------|------------------|---------------------|
| `API_HOST`  | `localhost`       | Backend host        |
| `API_PORT`  | `8000`            | Backend port        |

## Task weights

| Task               | Weight | Description                           |
|--------------------|--------|---------------------------------------|
| `analyze_tire`     | 3      | Upload synthetic tire image           |
| `get_history`      | 2      | Paginated analysis history            |
| `check_health`     | 1      | Liveness probe                        |
| `submit_feedback`  | 1      | Submit user correction                |
| `view_dashboard`   | 1      | Enterprise dashboard data             |
