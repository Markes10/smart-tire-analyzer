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

# Create secrets from .env file
kubectl create secret generic smart-tire-backend-secrets \
  --namespace=smart-tire \
  --from-literal=GEMINI_API_KEYS="your_key" \
  --from-literal=GOOGLE_MAPS_API_KEYS="your_key" \
  --from-literal=OPENWEATHER_API_KEYS="your_key" \
  --from-literal=MAPILLARY_API_KEYS="your_key" \
  --from-literal=JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"

kubectl create secret generic smart-tire-frontend-secrets \
  --namespace=smart-tire \
  --from-literal=NEXTAUTH_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
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

### 5. Apply Network Policies

```bash
kubectl apply -f deployment/kubernetes/network-policy.yaml
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

---

## TLS / HTTPS Setup

### Docker Deployment (Development)

Generate self-signed certificates for local HTTPS testing:

```bash
# Generate development certificates
bash scripts/generate_dev_certs.sh

# OR let docker-compose auto-generate them on first start
docker compose -f deployment/docker/docker-compose.yml up -d
# The 'cert-gen' service creates certificates in ./certs/

# Trust the CA certificate in your browser (to avoid "Not Secure" warnings):
#   Windows:   double-click certs/ca.crt → Install Certificate →
#              Local Machine → Trusted Root Certification Authorities
#   macOS:     sudo security add-trusted-cert -d -r trustRoot \
#                -k /Library/Keychains/System.keychain certs/ca.crt
#   Linux:     sudo cp certs/ca.crt /usr/local/share/ca-certificates/ \
#                && sudo update-ca-certificates
```

After generating certs, the nginx container serves both:
- **Port 80**: Plain HTTP (proxied to backend)
- **Port 443**: HTTPS with TLS (auto-detects certs in `/etc/nginx/ssl/`)

Set `ENABLE_HTTPS=true` in your `.env` file to have the port-80 server redirect HTTP → HTTPS.

### Docker Deployment (Production — Let's Encrypt)

For production with a real domain, use Certbot to obtain trusted certificates:

```bash
# 1. Run the production setup script
bash scripts/setup_production_certs.sh your-domain.com

# 2. This will:
#    - Obtain Let's Encrypt certificates via ACME HTTP-01 challenge
#    - Store certs in /etc/letsencrypt/live/your-domain.com/
#    - Set up auto-renewal via systemd timer or cron

# 3. Update nginx.conf:
#    - Change server_name to your domain
#    - Uncomment production certificate paths
#    See deployment/docker/nginx.conf for instructions

# 4. Update .env:
#    DOMAIN=your-domain.com
#    ENABLE_HTTPS=true

# 5. Restart the stack:
#    docker compose -f deployment/docker/docker-compose.yml up -d
```

### Kubernetes Deployment (cert-manager + Let's Encrypt)

#### 1. Install cert-manager

```bash
# Install cert-manager into your cluster
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Verify installation
kubectl get pods -n cert-manager
```

#### 2. Install Ingress Controller

```bash
# Install nginx ingress controller (pick the correct provider)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Get the ingress controller's external IP
kubectl get svc -n ingress-nginx
```

#### 3. Configure DNS

Create an A record for your domain pointing to the ingress controller's external IP:

```
your-domain.com  A  <INGRESS_CONTROLLER_EXTERNAL_IP>
```

#### 4. Update issuer email and domain

Edit these files to replace placeholder values:
- `deployment/kubernetes/cert-manager-issuer.yaml` — set `email` address
- `deployment/kubernetes/ingress.yaml` — replace `YOUR_DOMAIN.com` with your domain
- `deployment/kubernetes/frontend-deployment.yaml` — set `NEXTAUTH_URL` to your HTTPS domain
- `deployment/kubernetes/deployment.yaml` — update `BACKEND_CORS_ORIGINS` to include your domain

#### 5. Apply TLS resources

```bash
# 1. Create the Let's Encrypt ClusterIssuer
kubectl apply -f deployment/kubernetes/cert-manager-issuer.yaml

# 2. Deploy the app (if not already deployed)
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/frontend-deployment.yaml

# 3. Create the Ingress resources — triggers certificate issuance
kubectl apply -f deployment/kubernetes/ingress.yaml
```

#### 6. Verify certificate issuance

```bash
# Check certificate status
kubectl get certificate -n smart-tire
kubectl describe certificate smart-tire-tls -n smart-tire

# Check ingress
kubectl get ingress -n smart-tire

# Test HTTPS
curl https://your-domain.com/health
```

### Testing with Staging Issuer

Before switching to the production Let's Encrypt issuer (which has rate limits of 50 certificates per week per domain), test with the staging issuer:

1. In `deployment/kubernetes/ingress.yaml`, change:
   ```yaml
   cert-manager.io/cluster-issuer: "letsencrypt-prod"
   ```
   to:
   ```yaml
   cert-manager.io/cluster-issuer: "letsencrypt-staging"
   ```

2. Reapply: `kubectl apply -f deployment/kubernetes/ingress.yaml`

3. Verify the staging certificate is issued (`kubectl describe certificate`).

4. Once staging works, switch back to `letsencrypt-prod` and reapply.

### Certificate Auto-Renewal

#### Docker (Certbot)

Certbot installs a systemd timer that automatically renews certificates before they expire. To verify:

```bash
# Check the certbot timer
sudo systemctl status certbot.timer

# Test renewal process (dry run)
sudo certbot renew --dry-run
```

If your system doesn't use systemd, the setup script installs a cron job that runs daily at 3 AM:

```cron
0 3 * * * root certbot renew --quiet --post-hook 'docker compose -f /path/to/docker-compose.yml restart nginx'
```

#### Kubernetes (cert-manager)

cert-manager automatically monitors certificate expiry and renews certificates before they expire (typically 30 days before expiry). No manual intervention is needed.

To verify auto-renewal is working:

```bash
# Check certificate expiry
kubectl get certificate -n smart-tire -o wide

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50

# Manually trigger renewal check
kubectl cert-manager renew smart-tire-tls -n smart-tire
```

### Troubleshooting TLS

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Chrome shows "NET::ERR_CERT_AUTHORITY_INVALID" | Self-signed cert not trusted | Install `ca.crt` in OS trust store (see above) |
| `curl: (60) SSL certificate problem` | CA not trusted | Use `curl -k` for dev, or trust the CA |
| Certificate not issued (K8s) | DNS not pointing to ingress IP | Verify A record |
| Certificate stuck on "Issuing" | ACME challenge failed | `kubectl describe order -n smart-tire` |
| "No valid challenges" | NetworkPolicy blocking ACME | Check `deny-all-egress` allows port 80/443 to internet |
| HSTS preventing HTTP access | Browser cached HSTS | Clear HSTS: `chrome://net-internals/#hsts` → Delete domain |
| cert-manager pod can't reach ingress | NetworkPolicy too strict | Check `allow-cert-manager-webhook` and `allow-ingress-controller` policies |

---

## Health Monitoring

```bash
# Check all component status
curl https://localhost/health  # or http://localhost:8000 without TLS
curl https://localhost/health | python -m json.tool

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
