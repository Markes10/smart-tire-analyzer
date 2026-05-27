# Smart Tire Analyzer

<div align="center">
  <h3>🚗 AI-Powered Cross-Platform Tire Intelligence System</h3>
  <p>
    CNN + Vision Transformer + RNN + ANN · Gemini AI Reasoning · Self-Correcting Learning
  </p>
</div>

---

## Overview

**Smart Tire Analyzer** is a production-grade, cross-platform AI system that analyzes tire condition from photographs using a hybrid deep learning model (CNN + ViT + RNN + ANN). It predicts tread depth, health score, remaining life, and wear pattern — then enriches results with Gemini AI reasoning, Google Maps road context, and live weather data.

### ✅ What It Does

| Feature | Detail |
|---|---|
| **Tread Depth Prediction** | 4-point measurement (T1–T4), MAE < 0.5mm |
| **Health Score** | 0–10 scale with Monte Carlo uncertainty |
| **Remaining Life** | km estimate adjusted for road + weather conditions |
| **Wear Pattern Detection** | 6 classes: center, edge, patchy, uniform, one-side, cupping |
| **Gemini AI Reasoning** | Context-aware driving advice and replacement urgency |
| **Road Context** | Google Maps terrain + road surface + traffic |
| **Weather Context** | Rain, temperature, visibility from OpenWeatherMap |
| **Continuous Learning** | Session corrections stored → auto-retrain after 10 trainable samples |
| **TurboQuant** | FP16 + INT8 quantization for mobile deployment |

---

## Final Year Project Enterprise Upgrade

The project now includes a local-runnable enterprise AI layer for final-year-project presentation:

| Upgrade | Added implementation |
|---|---|
| MLOps Pipeline | `/enterprise/dashboard`, `scripts/mlops_pipeline.py`, local experiment events, model registry snapshot, DVC/Airflow/Kubeflow skeletons |
| Edge AI | ONNX/TensorRT/Jetson/mobile inference readiness metadata and offline prediction workflow |
| Explainable AI | Grad-CAM/SHAP/attention-style region metadata in every analysis report |
| Confidence Scoring | Prediction confidence %, uncertainty %, and failure risk score |
| Digital Twin | Physical tire state mirrored into a virtual tire lifecycle simulation |
| Predictive Analytics | Remaining useful life, failure forecast window, and trend analysis |
| IoT Fusion | Optional pressure, temperature, vibration, and speed fields in `/analyze` |
| Cloud Native | Docker, Kubernetes, and microservice deployment status |
| Security | Optional JWT/RBAC middleware with local demo token endpoint |
| Monitoring | `/dashboard` frontend plus drift, health, GPU, latency, and error-log status |
| Multi-Agent AI | Damage, maintenance, cost, and report-generation agents |
| Federated Learning | Local secure-aggregation simulation status |
| Knowledge Graph / RAG | Local maintenance knowledge retrieval with FAISS/Pinecone-ready design |
| AI Report Generation | Technician notes and PDF-ready report metadata |
| Synthetic Data | GAN/diffusion/augmentation research plan and output path |

Open the dashboard at `http://127.0.0.1:3000/dashboard` after running `run_services.bat`.
See `docs/FINAL_YEAR_PROJECT_ARCHITECTURE.md` for the architecture explanation.

---

## Architecture

```
📷 Tire Image
       ↓
[10-Step Preprocessing Pipeline]
  1. Blur Detection (reject < 100 Laplacian variance)
  2. Tire Detection + Crop
  3. Perspective Correction
  4. Noise Reduction (NL-Means)
  5. CLAHE Enhancement
  6. Sharpening Filter
  7. Edge Detection for runtime depth estimation
  8. Resize (224x224)
  9. Normalization (ImageNet stats)
  10. Augmentation (training only)
       ↓
[CNN: EfficientNetV2-B0] -> 512-dim local tread features
[Transformer: ViT-B/16] -> 512-dim global tread pattern features
[RNN: BiLSTM + TCN] -> 256-dim sequential tread features
       ↓
[Fusion: Cross-Modal Attention + Deep Dense ANN]
       ↓
[Prediction Heads]
  ├── Tread Depth (×4 regression)
  ├── Health Score (regression)
  ├── Remaining Life (regression)
  └── Wear Pattern (6-class classification)
       ↓
[Gemini AI Reasoning + Maps + Weather]
       ↓
📊 Final Report
```

| Component | Selected Model | Role |
|---|---|---|
| CNN | EfficientNetV2-B0 | Local tread feature extraction |
| Transformer | ViT-B/16 | Global tread pattern understanding |
| RNN | BiLSTM + TCN | Sequential tread analysis |
| ANN | Cross-Modal Attention + Deep Dense Fusion | Final prediction fusion |

---

## Quick Start

### 1. Setup Environment

```bash
git clone <repo-url>
cd smart-tire-analyzer

# One-command setup (creates venv, installs deps, creates dirs)
python scripts/setup_env.py
```

### 2. Configure API Keys

```bash
# Edit the generated .env file
notepad .env       # Windows
nano .env          # Linux/macOS
```

Add your API keys:
```
GEMINI_API_KEY=your_key_here
GOOGLE_MAPS_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
```

### 3. Start Backend

```bash
# Development
python scripts/start_server.py

# Production
python scripts/start_server.py --prod --workers 4
```

**API is live at:** `http://localhost:8000`  
**Swagger docs:** `http://localhost:8000/docs`

### 4. Test Inference

```bash
# Analyze a tire image locally
python scripts/infer.py --image path/to/tire.jpg

# With GPS context
python scripts/infer.py --image tire.jpg --lat 28.61 --lon 77.21
```

### 5. Run Tests

```bash
python scripts/run_tests.py
```

---

## Docker Deployment

```bash
# Build and start all services
docker compose -f deployment/docker/docker-compose.yml up --build -d

# Check health
curl http://localhost:8000/health
```

---

## API Reference

### `POST /analyze`

Upload a tire image and receive a complete analysis report.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | ✅ | JPEG/PNG, max 10MB |
| `latitude` | float | ❌ | GPS for road context |
| `longitude` | float | ❌ | GPS for road context |
| `tire_brand` | string | ❌ | e.g. "Michelin" |
| `mileage_km` | float | ❌ | Current vehicle mileage |

**Response:** Full analysis JSON with risk level, predictions, reasoning, and alerts.

### `POST /feedback`

Submit user correction for continuous learning.

```json
{
  "session_id": "uuid",
  "feedback_type": "wrong",
  "corrected_tread_depth_mm": 4.5,
  "corrected_wear_pattern": "edge_wear"
}
```

### `GET /history`

Retrieve paginated analysis history.

```
GET /history?page=1&page_size=20&risk_level=HIGH
```

### `GET /health`

Service health check.

---

## Frontend (Next.js Web UI)

The repository contains a Next.js web UI in the `frontend/` directory.

- Install dependencies:
       - `cd frontend`
       - `npm install`
- Development server:
       - `npm run dev -- -p 8081`  # starts at http://localhost:8081
- Production build:
       - `npm run build`
       - `npm start`    # serves the optimized build
- Environment:
       - Optional: set `NEXT_PUBLIC_API_BASE_URL` to point the UI to the backend API (default: `http://localhost:8000`).

Notes:
- The Next.js app uses Node/Next 16 and React 19; use `npm` (or `pnpm`/`yarn`) to install.
- If you plan to run the frontend separately, ensure the backend API is accessible and any required API keys are set on the backend.

Runs on: **Web (Chrome/Safari/Edge)** | **Windows** | **ChromeOS**

---

## AI Training

```bash
# Fresh PyTorch hybrid training (EfficientNetV2-B0 + ViT-B/16 + BiLSTM + TCN + attention fusion)
.\.venv\Scripts\python.exe scripts\prepare_and_train.py --fresh-hybrid --archive-old --full-train

# Outputs
# ai_model/saved_models/hybrid_torch/model_best.pt
# ai_model/saved_models/hybrid_torch/metadata.json
# ai_model/saved_models/hybrid_torch/metrics.json

# Quick smoke run without archiving old artifacts
.\.venv\Scripts\python.exe scripts\prepare_and_train.py --fresh-hybrid --hybrid-stage1-epochs 1 --hybrid-stage2-epochs 0
```

---

## Continuous Learning

The self-correcting pipeline works automatically:

1. Users submit corrections via `POST /feedback`
2. Corrected image labels accumulate in `dataset/continuous_learning/labels.csv`
3. After **10 trainable corrected samples**, hybrid retraining triggers automatically
4. New model is gated by acceptance metrics before becoming the preferred runtime checkpoint
5. Full versioning with rollback support in `continuous_learning/model_versions/`

---

## Cross-Platform Support

| Platform | Method | Status |
|---|---|---|
| Windows | Docker / `start_server.py` | ✅ |
| Linux | Docker / `start_server.py` | ✅ |
| macOS | Docker / `start_server.py` | ✅ |
| Web | Next.js | ✅ |
| ChromeOS | Next.js / Docker | ✅ |

---

## Project Structure

```
smart-tire-analyzer/
├── ai_model/
│   ├── cnn/            # legacy CNN helpers + preprocessing + augmentation
│   ├── transformer/    # Vision Transformer encoder
│   ├── rnn/            # BiLSTM tread sequence analysis
│   ├── ann/            # Fusion + multi-task prediction heads
│   ├── training/       # Train loop, loss, optimizer, callbacks
│   ├── evaluation/     # Metrics, confusion matrix, GradCAM
│   └── optimization/   # TurboQuant: FP16, INT8, TFLite
├── backend/
│   └── app/
│       ├── routes/     # /analyze, /feedback, /history, /health
│       ├── services/   # Inference, Gemini, Maps, Weather, Report
│       ├── models/     # Pydantic request/response schemas
│       └── database/   # SQLAlchemy models + CRUD
├── frontend/
│   └── src/
│       ├── screens/    # HomeScreen, CameraScreen, ResultScreen
│       ├── components/ # TireHealthGauge, WearPatternCard, RiskBadge
│       ├── api/        # analyze.ts, feedback.ts, client.ts
│       ├── store/      # Zustand: useAnalysisStore, useHistoryStore
│       └── utils/      # imageHelpers, depthClassifier
├── continuous_learning/
│   ├── wrong_predictions/  # store_wrong.py
│   ├── retraining/         # retrain_trigger, incremental_train, validation_check
│   └── model_versions/     # version_manager.py
├── api_integrations/
│   ├── gemini/         # gemini_client, prompt_builder, response_parser
│   ├── google_maps/    # maps_client, terrain_analyzer, traffic_fetcher
│   └── weather/        # weather_client, risk_scorer
├── dataset/
│   ├── images/         # Raw tire images
│   ├── labels/         # CSV label files
│   └── preprocessing/  # clean_dataset.py, split_dataset.py
├── configs/            # model_config.yaml, training_config.yaml, api_config.yaml
├── deployment/
│   ├── docker/         # Dockerfile, docker-compose.yml
│   ├── kubernetes/     # deployment.yaml, service.yaml, hpa.yaml
│   └── ci_cd/          # GitHub Actions workflows
├── scripts/            # setup_env.py, start_server.py, infer.py, run_tests.py
├── tests/              # test_api.py
├── .env.example        # API key template
└── pyproject.toml
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
