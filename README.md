# Smart Tire Analyser

<div align="center">
  <h3>AI-Powered Cross-Platform Tire Intelligence System</h3>
  <p>
    59 Model Architectures · Auto Model Selection · CNN + RNN + ANN · Gemini AI Reasoning
  </p>
  <p>
    <strong>Live Chat</strong> (Llama 3.3 tire-only AI) · <strong>Voice AI Support</strong> (OmniDimension)
  </p>
</div>

---

## Overview

**Smart Tire Analyser ** analyses tyre condition from photographs using a hybrid deep learning model with **automatic architecture selection**. It supports 59 model variants (22 CNN, 12 Transformer, 9 RNN, 16 Fusion/ANN) and includes a Next.js frontend with Live Chat and a Voice AI Support agent.

### Current Test Performance (767-image dataset)

| Metric | Accuracy |
|--------|:--------:|
| **Condition** (safe/moderate/replace) | **90.7%** |
| **Wear Pattern** (6 classes) | **61.7%** |
| **Tread Depth MAE** | **1.55 mm** |
| **Health Score MAE** | 0.43 |
| **Remaining Life MAE** | ~3,964 km |

### Key Features

| Feature | Detail |
|---------|--------|
| **Auto Model Selection** | Picks optimal CNN + RNN + ANN by dataset size (6 tiers) |
| **59 Model Architectures** | 22 CNN · 12 Transformer · 9 RNN · 16 Fusion/ANN |
| **Tread Depth Prediction** | 4-point measurement (T1–T4) |
| **Condition Classification** | 3 classes: safe, moderate, replace |
| **Wear Pattern Detection** | 6 classes: centre, edge, patchy, uniform, one-side, cupping |
| **24-Step Preprocessing** | Auto-rotate, shadow removal, GrabCut, CLAHE, edge detect, etc. |
| **Class-Weighted Training** | Inverse-frequency weighting for imbalanced classes |
| **Gemini AI Reasoning** | Context-aware driving advice and replacement urgency |
| **Continuous Learning** | User corrections → auto-retrain after 10 samples |
| **Live Chat** | Llama 3.3 tire-only AI assistant on `/live-chat` |
| **Voice AI Support** | OmniDimension voice agent (Llama 3.3 70B) on `/technical-support` |

---

## Architecture

Below are three focused architecture views you can copy into design docs or use for onboarding: System Architecture (components and deployment), Workflow Architecture (runtime flows for major scenarios), and Data Flow Architecture (how data moves, storage, and model lifecycle).

### 1) System Architecture

High-level components and how they are deployed/connected:

```
+----------------------+     +---------------------+     +--------------------------+
|  Frontend (Next.js)  |<--->|  Backend API (FastAPI)|<--->|  Model Serving & Inference |
|  (frontend/)         |     |  (backend/app/)      |     |  (ai_model/hybrid_torch/) |
+----------------------+     +---------------------+     +--------------------------+
         |  ^                         |  ^                       |  ^
         |  |                         |  |                       |  |
         v  |                         v  |                       v  |
+----------------------+     +---------------------+     +--------------------------+
| Live Chat (Llama)    |     |  External Services  |     |  Model Registry & ML-Ops  |
| (llama3.3 via Ollama) |     |  - Gemini / Maps     |     |  (mlops/, deployment/)    |
+----------------------+     |  - OmniDimension     |     +--------------------------+
                             |  - Weather API        |
                             +---------------------+

Optional on-device: Android app (android-app/) with TFLite models for offline inference.
```

Components (short):
- Frontend: Next.js app serving UI, Live Chat page, Technical Support voice page. Connects to backend via REST/WebSockets.
- Backend API: FastAPI app exposing /analyze, /feedback, /history, /health and Swagger. Orchestrates inference, LLM reasoning, maps/weather lookups, and feedback ingestion.
- Model Serving / Training: Training pipelines live in ai_model/hybrid_torch/, training orchestrated by scripts and mlops. Inference runs as part of the backend using loaded PyTorch checkpoints; optionally served via a model server or batch worker.
- External LLMs & Services: Gemini (for reasoning), Ollama-hosted Llama 3.3 for local live-chat, OmniDimension for voice, third-party Maps/Weather for contextualization.
- On-device Android App: TFLite models in android-app/assets for fast offline scans.
- Persistence & Observability: Postgres/Cloud storage for session/history, S3/DVC for datasets and model artefacts, Prometheus metrics endpoint.

Deployment notes:
- Docker Compose for local stack (deployment/docker/docker-compose.yml).
- Production can split components: frontend CDN + Vercel/Netlify, backend on Kubernetes, model training on GPU cluster, model registry in S3 + metadata DB.


### 2) Workflow Architecture

Three common runtime workflows show component interactions and primary steps.

A) Inference (user uploads image via web or mobile):
1. User uploads image (frontend → backend /analyze).
2. Backend receives image, stores raw image (temp or object store).
3. Preprocessing pipeline (backend or inference worker) runs the 24-step preprocessing (rotation, shadow removal, GrabCut, CLAHE, edge detection).
4. Backend loads the active model (ai_model/saved_models) or calls the model-serving endpoint and runs inference -> predictions (tread depths, wear, health, remaining life, condition).
5. Backend calls Gemini/LLM to attach human-readable reasoning and map/weather enrichment.
6. Compose analysis report and return to frontend; persist session and metrics to DB; emit Prometheus metrics.

B) Continuous Learning (user feedback → model update):
1. User submits correction via frontend -> POST /feedback.
2. Backend validates and stores feedback as a labelled example in `dataset/continuous/` or a feedback queue.
3. MLOps orchestrator (mlops/) periodically pulls queued feedback; when collected N new samples (configurable, default 10), it triggers `train_new_models.py` or `scripts/train_smart.py` for incremental retraining.
4. Training produces a new checkpoint and metadata in `ai_model/saved_models/`; ML-Ops updates the model registry and promotes to staging/production after validation tests.
5. Backend refreshes active model (hot-swap or restart) and old model is archived.

C) Live Chat / Voice Support:
1. User opens Live Chat (frontend) -> connects to live-chat API route.
2. Frontend forwards messages to local Ollama (llama3.3) or to a hosted provider with a strict tire-only system prompt.
3. The chat assistant can request context (session_id) from the backend to fetch analysis results and offer reasoning; voice flows use OmniDimension integration.
4. Chat/voice responses returned to frontend; optionally logged to improve prompts and analytics.


### 3) Data Flow Architecture

This describes data stores, movement, and retention for images, labels, models, and telemetry.

```
User Image --(upload)--> Backend Temp Storage ---> Object Store (S3/DVC) ---> Preprocessing --> Feature tensors
                                                              |                               |
                                                              v                               v
                                                     Dataset (dataset/splits/)           Model Training Pipeline
                                                              |                               |
                                                  Labels & Feedback <---- Feedback Queue <-- User Corrections
                                                              |
                                                              v
                                                    Model Artifacts (ai_model/saved_models/) --> Model Registry (mlops/)
                                                              |
                                                              v
                                                Deployment (backend model loader, android-app TFLite)
```

Data stores and retention:
- Raw images: uploaded images are stored in a short-term object store (e.g., S3) for reproducible preprocessing; retention configurable (e.g., 30–90 days) unless attached to labelled datasets.
- Processed artefacts: cached preprocessing outputs and tensors may be stored in a dataset bucket or ephemeral cache to speed training and inference.
- Labels & feedback: stored in Postgres or a labelling DB and mirrored to dataset/splits/ for training. Feedback includes session_id, corrected fields, user metadata (anonymised if required).
- Models: checkpoints, metadata.json, metrics.json, history.json stored in ai_model/saved_models/ and synced to model registry (S3 + metadata DB). Each model has semantic tags: tier, dataset_size, timestamp, validation metrics.
- Telemetry & metrics: Prometheus for runtime metrics, ELK/Cloud logging for traces, and periodic evaluation metrics stored with model artifacts.

Security & privacy considerations:
- Image PHI: treat images as personal data; redaction and retention policies applied.
- API auth: JWT or API key (`AUTH_ENABLED` controls enforcement). Use HTTPS and rotate keys.
- LLM access: restrict LLM prompts and do not send raw user identities to third-party LLM providers.


---

## Quick Start

### 1. Setup Environment

```bash
git clone <repo-url>
cd smart-tire-analyzer

# Create virtual environment + install deps
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r backend/requirements.txt
pip install -r ai_model/hybrid_torch/requirements.txt
```

### 2. Place Dataset

Add tire images with labels to `dataset/splits/`:

```
dataset/splits/
├── train/labels.csv      # Training set
├── validation/labels.csv # Validation set
└── test/labels.csv       # Test set
```

Each CSV must include `image_path`, `condition_id` (0=safe,1=moderate,2=replace), `wear_pattern`, and tread columns (`tread_1`–`tread_4`).

### 3. Smart Training (Auto Model Selection)

```bash
# Full training with auto-config
python scripts/train_smart.py

# Analysis only (no training)
python scripts/train_smart.py --analyze
```

The system will:
- Count your samples and classify into a tier
- Select optimal CNN + RNN + Fusion (and Transformer if enough data)
- Train in two stages: frozen encoder (30 epochs) → fine-tune (25 epochs)
- Apply class-weighted loss to handle imbalance
- Save best checkpoint to `ai_model/saved_models/hybrid_torch/`

### 4. Start Backend

```bash
python scripts/start_server.py
```

**API:** `http://localhost:8000`  
**Swagger:** `http://localhost:8000/docs`

### 5. Start Frontend (optional)

```bash
cd frontend
npm install
npm run dev
```

**Frontend:** `http://localhost:3000`  
**Live Chat:** `http://localhost:3000/live-chat`  
**Technical Support:** `http://localhost:3000/technical-support` (with Voice AI)

### 6. Test Inference

```bash
# Analyze a tire image
python scripts/infer.py --image path/to/tire.jpg

# With GPS context
python scripts/infer.py --image tire.jpg --lat 28.61 --lon 77.21
```

Or double-click `run_services.bat` and choose **Local Dev Mode**.

---

## Training Details

### Loss Function

Multi-task loss with class-weighted cross-entropy for imbalance:

| Component | Weight | Notes |
|-----------|:------:|-------|
| Tread Depth L1 | 3.5 | Smooth L1 + extra penalty for >1mm error |
| Health MSE | 0.7 | |
| Remaining Life MSE | 0.7 | |
| Wear Pattern CE | 1.0 | Inverse-frequency class weighted |
| Condition CE | 1.0 | Inverse-frequency class weighted |

Class weights are computed from the training set distribution (e.g., "replace" condition gets ~3.5× weight vs "safe").

### Training Stages

1. **Stage 1** (30 epochs): Frozen pretrained encoder, trains heads + fusion + RNN
2. **Stage 2** (25 epochs): Fine-tune last 3 CNN blocks + all heads

### Outputs

```
ai_model/saved_models/hybrid_torch/
├── model_best.pt            # Best checkpoint (by tread MAE)
├── model_last.pt            # Last checkpoint
├── metadata.json            # Architecture + hyperparams + calibration
├── metrics.json             # Validation/test metrics
├── history.json             # Per-epoch training history
└── tread_calibration.json   # Isotonic regression calibrator
```

---

## Docker Deployment

```bash
docker compose -f deployment/docker/docker-compose.yml up --build -d
curl http://localhost:8000/health
```

---

## API Reference

### `POST /analyze`

Upload a tire image → analysis report.

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | ✅ | JPEG/PNG, max 10MB |
| `latitude` | float | ❌ | GPS for road context |
| `longitude` | float | ❌ | GPS for road context |
| `tire_brand` | string | ❌ | e.g. "Michelin" |
| `mileage_km` | float | ❌ | Current mileage |

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

Paginated analysis history.

### `GET /health`

Service health check.

---

## Project Structure

```
smart-tire-analyzer/
├── ai_model/
│   ├── models/            # 59 model implementations (CNN, RNN, Fusion)
│   ├── hybrid_torch/      # Training pipeline, dataset, evaluation
│   │   ├── trainer.py     # Multi-task training with class weighting
│   │   ├── model.py       # Model architecture + checkpoint loading
│   │   ├── dataset.py     # HybridTireDataset with tread sequences
│   │   └── constants.py   # Labels, aliases, hyperparams
│   ├── model_selector.py  # Auto-architecture recommender
│   └── saved_models/      # Trained model checkpoints
├── backend/
│   └── app/
│       ├── routes/        # /analyze, /feedback, /history, /health, /support
│       ├── services/      # Inference, Gemini, Maps, Weather, Omnidim
│       └── models/        # Pydantic schemas
├── frontend/
│   └── app/
│       ├── api/live-chat/ # Llama 3.3 tire-only AI assistant API
│       ├── live-chat/     # Live Chat page
│       ├── contact/       # Contact page
│       ├── technical-support/ # Technical Support + Voice AI
│       └── ...            # Other pages (home, documentation, etc.)
├── dataset/
│   ├── splits/            # train/val/test CSVs with image paths
│   ├── preprocessing/     # Pipeline: rotation, shadow, GrabCut, etc.
│   └── raw/               # Raw tread images
├── scripts/
│   ├── train_smart.py     # Smart training entry point
│   ├── start_server.py    # Backend API server
│   ├── infer.py           # Local inference
│   └── setup_env.py       # Environment setup
├── deployment/
│   └── docker/            # Dockerfile + compose
├── debug_root.bat         # System diagnostics
├── run_services.bat       # Interactive launcher (Windows)
└── README.md
```

# Markus Lee 
# viren_22co72
# Shubham Chodankar
---

## License

MIT License — see [LICENSE](LICENSE) for details.
