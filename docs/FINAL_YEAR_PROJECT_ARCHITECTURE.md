# Smart Tire Analyzer - Final Year Project Architecture

## Project Scope

Smart Tire Analyzer is now structured as a local-runnable final-year project with enterprise-grade architecture blocks. The core app still runs on a laptop using FastAPI, Next.js, SQLite, and the existing hybrid tire model. Heavy enterprise platforms are optional adapters so the demo does not break when MLflow, W&B, Airflow, Kubeflow, DVC, TensorRT, or Jetson hardware are not installed.

## Enterprise Workflow

```text
Data Versioning
  -> Model Training
  -> Experiment Tracking
  -> Model Registry
  -> CI/CD Deployment
  -> Monitoring
  -> Auto Retraining
```

## Added Architecture Blocks

| Block | Local implementation | Enterprise tools represented |
|---|---|---|
| MLOps & Model Lifecycle Management | `/enterprise/dashboard`, `scripts/mlops_pipeline.py`, local registry snapshot | MLflow, W&B, DVC, Kubeflow, Airflow |
| Edge AI Processing | Edge status and offline prediction workflow metadata | ONNX Runtime, TensorRT, NVIDIA Jetson, mobile inference |
| Explainable AI | XAI region metadata and image edge-attention summary | Grad-CAM, SHAP, attention heatmaps |
| Confidence Scoring | Confidence %, uncertainty %, failure risk score | Calibration and uncertainty estimation |
| Digital Twin | Physical tire state mirrored into a virtual lifecycle simulation | Industry 4.0 digital twin pattern |
| Predictive Maintenance | RUL, failure forecast window, trend analysis | Predictive analytics engine |
| IoT Sensor Fusion | Pressure, temperature, vibration, and speed form fields | Multimodal image + sensor AI |
| Cloud Native | Docker and Kubernetes assets already included | Microservices, Docker, Kubernetes |
| Security | Optional JWT/RBAC middleware with demo token endpoint | OAuth2/JWT/RBAC/API gateway pattern |
| Monitoring Dashboard | `/dashboard` frontend and `/enterprise/dashboard` API | Drift, health, GPU, latency, error logs |
| Multi-Agent AI | Four report agents in analysis metadata | Damage, maintenance, cost, report agents |
| Federated Learning | Local simulation status and node count | Secure vehicle-side learning |
| Knowledge Graph / RAG | Local maintenance knowledge retrieval | FAISS/Pinecone-ready RAG design |
| AI Report Generation | Technician notes and PDF-ready output metadata | Llama/Ollama report generator |
| Synthetic Data Engine | Synthetic data plan and augmentation path | GANs, diffusion, data augmentation |

## Local Demo Commands

Start the full app:

```bat
run_services.bat
```

Open:

```text
Frontend: http://127.0.0.1:3000
Dashboard: http://127.0.0.1:3000/dashboard
Backend API: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
```

Run the local MLOps snapshot:

```bash
python scripts/mlops_pipeline.py
```

Try the enterprise simulation endpoint:

```bash
curl -X POST http://127.0.0.1:8000/enterprise/simulate ^
  -H "Content-Type: application/json" ^
  -d "{\"risk_level\":\"HIGH\",\"confidence\":0.92,\"tire_pressure_psi\":28,\"temperature_c\":55,\"vibration_g\":1.4}"
```

## Security Demo

The API remains open by default for local demos.

To enable token protection:

```env
AUTH_ENABLED=true
JWT_SECRET=change-this-secret
```

Generate a token:

```text
GET /enterprise/security/demo-token?role=technician
```

Then call protected endpoints with:

```text
Authorization: Bearer <token>
```

## Report Output Upgrade

Every successful `/analyze` response now includes:

```json
{
  "enterprise_ai": {
    "mlops_lifecycle": {},
    "edge_ai": {},
    "explainable_ai": {},
    "confidence_estimation": {},
    "digital_twin": {},
    "predictive_maintenance": {},
    "iot_sensor_fusion": {},
    "cloud_native": {},
    "security": {},
    "monitoring": {},
    "multi_agent_ai": {},
    "federated_learning": {},
    "rag_knowledge_base": {},
    "llm_report_generator": {},
    "synthetic_data_engine": {}
  }
}
```
