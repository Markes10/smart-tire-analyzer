# Smart Tire Analyzer — Deployment Guide

## Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| Docker | 24.0+ | Container deployment |
| Docker Compose | 2.20+ | Multi-service orchestration |
| Node.js | 18.0+ | Frontend build |
| Git | 2.40+ | Version control |

---

## Local Development (Without Docker)

### 1. Setup

```bash
cd smart-tire-analyzer
python scripts/setup_env.py
```

### 2. Activate virtual environment

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### 3. Configure API keys

```bash
cp .env.example .env
# Edit .env with your keys
```

### 4. Start backend

```bash
python scripts/start_server.py
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 5. Start frontend

```bash
cd frontend
npm install
npx expo start
# Press A for Android, I for iOS, W for Web
```

---

## Docker Deployment (Recommended)

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with real API keys

# 2. Build and start
docker compose -f deployment/docker/docker-compose.yml up --build -d

# 3. Verify
curl http://localhost/health
curl http://localhost/docs

# 4. View logs
docker compose -f deployment/docker/docker-compose.yml logs -f backend
```

### Stopping

```bash
docker compose -f deployment/docker/docker-compose.yml down
```

### Updating

```bash
docker compose -f deployment/docker/docker-compose.yml pull
docker compose -f deployment/docker/docker-compose.yml up -d --build
```

---

## Kubernetes Deployment

### 1. Create namespace and secrets

```bash
kubectl apply -f deployment/kubernetes/service.yaml  # Creates namespace

kubectl create secret generic smart-tire-secrets \
  --namespace=smart-tire \
  --from-literal=gemini-api-key=your_key \
  --from-literal=maps-api-key=your_key \
  --from-literal=weather-api-key=your_key \
  --from-literal=database-url=postgresql+asyncpg://user:pass@host:5432/smart_tire
```

### 2. Deploy model storage

```bash
# Upload model files to PVC or object storage first
# Then apply deployment
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/hpa.yaml
```

### 3. Verify deployment

```bash
kubectl get pods -n smart-tire
kubectl get svc -n smart-tire
kubectl logs -f deployment/smart-tire-backend -n smart-tire
```

### 4. Scale manually

```bash
kubectl scale deployment smart-tire-backend --replicas=4 -n smart-tire
```

---

## CI/CD (GitHub Actions)

### Required Secrets

Set these in your GitHub repository → Settings → Secrets:

| Secret | Description |
|---|---|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password / access token |

### Workflows

| Workflow | Trigger | Action |
|---|---|---|
| `train.yml` | Push with dataset changes | Retrain model, export TFLite |
| `deploy.yml` | Push to main | Run tests, build Docker image, deploy |

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key |
| `GOOGLE_MAPS_API_KEY` | ✅ | — | Google Maps API key |
| `OPENWEATHER_API_KEY` | ✅ | — | OpenWeatherMap API key |
| `DATABASE_URL` | ❌ | SQLite | Database connection string |
| `API_PORT` | ❌ | 8000 | Backend port |
| `AUTO_RETRAIN` | ❌ | true | Enable continuous learning |
| `RETRAIN_THRESHOLD` | ❌ | 50 | Wrong predictions before retrain |

---

## Health Monitoring

```bash
# Check all component status
curl http://localhost:8000/health | python -m json.tool

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "00:05:32",
  "components": {
    "ai_model": "healthy",
    "database": "healthy",
    "api": "healthy"
  }
}
```

---

## Troubleshooting

### Backend won't start

```bash
# Check Python path
python --version  # Must be 3.10+

# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall

# Check .env file
cat .env | grep -v "^#" | grep -v "^$"
```

### Model not found

```bash
# Train a new model
python ai_model/training/train.py --epochs 5

# Or use the inference script (works without trained model)
python scripts/infer.py --image your_tire.jpg
```

### Image upload rejected (blur error)

- Ensure good lighting — avoid direct sunlight or flash glare
- Hold phone steady, let camera autofocus
- Photograph from 30–50cm distance
- Shoot at 90° angle directly at tread surface

### Frontend can't reach backend

```bash
# Update API base URL in frontend/.env or app.json
API_BASE_URL=http://YOUR_MACHINE_IP:8000

# For Android emulator connecting to local backend:
API_BASE_URL=http://10.0.2.2:8000
```
