# Smart Tire Analyzer — Production Readiness Checklist

> **Status:** ✅ Complete means verified and documented in the codebase.
> **Action:** Items you must configure or verify before going live.

---

## 1. ☸️ Infrastructure & Cluster

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1.1 | **Kubernetes cluster** provisioned (EKS, GKE, AKS, etc.) | ⬜ | Minimum 2 nodes, 4 vCPU, 8GB RAM each |
| 1.2 | **kubectl** configured and authenticated | ⬜ | `kubectl cluster-info` returns OK |
| 1.3 | **Cluster autoscaler** configured | ⬜ | For handling traffic spikes |
| 1.4 | **Node auto-repair** enabled (managed node groups) | ⬜ | Cloud provider specific |
| 1.5 | **Pod resource quotas** / limits set | ✅ | Defined in `deployment.yaml` |
| 1.6 | **Horizontal Pod Autoscaler** applied | ✅ | `deployment/kubernetes/hpa.yaml` |
| 1.7 | **Namespace** created (`smart-tire`) | ✅ | `deployment/kubernetes/service.yaml` |

---

## 2. 🔐 TLS / HTTPS

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 2.1 | **Domain** registered and DNS configured | ⬜ | A record → ingress controller external IP |
| 2.2 | **cert-manager** installed | ✅ | Script: `scripts/deploy_k8s_tls.sh` |
| 2.3 | **ingress-nginx** installed | ✅ | Script: `deploy_k8s_tls.sh` |
| 2.4 | **ClusterIssuer** applied (Let's Encrypt) | ✅ | `deployment/kubernetes/cert-manager-issuer.yaml` |
| 2.5 | **Ingress** with TLS annotation applied | ✅ | `deployment/kubernetes/ingress.yaml` |
| 2.6 | **Certificate** issued and valid | ⬜ | `kubectl get certificate -n smart-tire` |
| 2.7 | **HSTS** enabled (1 year, preload) | ✅ | Configured in ingress annotations |
| 2.8 | **TLS 1.2/1.3 only**, no weak ciphers | ✅ | Configured in ingress |
| 2.9 | **Auto-renewal** verified | ✅ | cert-manager auto-renews 30d before expiry |
| 2.10 | [Docker] **Certbot** set up for non-K8s | ✅ | `scripts/setup_production_certs.sh` |

---

## 3. 🔑 Authentication & Secrets

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 3.1 | **AUTH_ENABLED=true** | ✅ | `.env.production` |
| 3.2 | **JWT_SECRET** generated (≥32 chars) | ⬜ | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| 3.3 | **NEXTAUTH_SECRET** generated (≥32 chars) | ⬜ | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| 3.4 | **API keys** stored in K8s Secrets (not ConfigMaps) | ✅ | `deployment.yaml` uses `secretKeyRef` |
| 3.5 | **API keys encrypted at rest** in database | ✅ | Fernet (AES-256-GCM) from JWT_SECRET |
| 3.6 | **API keys never in browser** localStorage | ✅ | Only boolean preferences stored |
| 3.7 | **No hardcoded secrets** in deployment manifests | ✅ | All via `kubectl create secret` |
| 3.8 | **.gitignore** covers .env, .secrets.env, cert keys | ✅ | Verified in `.gitignore` |
| 3.9 | **Secrets file permissions** restricted (chmod 600) | ✅ | Documented in `.env.production` |

---

## 4. 🛡️ Network Security

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 4.1 | **NetworkPolicies** applied | ✅ | `deployment/kubernetes/network-policy.yaml` |
| 4.2 | **Deny-all ingress** by default | ✅ | Default deny with explicit allow rules |
| 4.3 | **Deny-all egress** by default | ✅ | Only internet (80/443) + pod-to-pod allowed |
| 4.4 | **Ingress controller** accessible (ports 80/443) | ✅ | NetworkPolicy allows ingress-nginx |
| 4.5 | **cert-manager** can reach ACME servers (80/443) | ✅ | Egress policy allows internet |
| 4.6 | **Redis** isolated (only backend can reach) | ✅ | NetworkPolicy restricts to backend pods |
| 4.7 | **CORS origins** restricted to known domains | ✅ | Set in `deployment.yaml` |
| 4.8 | **Rate limiting** configured (10 req/s, burst 20) | ✅ | Ingress annotations in `ingress.yaml` |
| 4.9 | **Pod security context** applied (non-root, read-only) | ✅ | Defined in `deployment.yaml` |

---

## 5. 🗄️ Database

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 5.1 | **PostgreSQL** (or managed DB) — SQLite not for prod | ✅ | Documented in `.env.production` |
| 5.2 | **Database encryption at rest** (RDS/Aurora/GCloud SQL) | ⬜ | Cloud provider specific |
| 5.3 | **TLS connection** to database | ⬜ | `DATABASE_URL=postgresql+asyncpg://...?ssl=true` |
| 5.4 | **Automated backups** configured | ⬜ | Daily backups with retention |
| 5.5 | **Connection pooling** with PgBouncer or similar | ⬜ | For high-concurrency scenarios |
| 5.6 | **Migration script** run on deploy | ✅ | `scripts/migrate_db.py` |
| 5.7 | **Read replica** for scaling queries | ⬜ | Optional, for heavy read workloads |

---

## 6. 📊 Monitoring & Observability

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 6.1 | **Prometheus** installed | ⬜ | Prometheus Operator recommended |
| 6.2 | **cert-manager metrics** scraped (PrometheusRules) | ✅ | `deployment/kubernetes/prometheus-rules.yaml` |
| 6.3 | **blackbox-exporter** deployed for endpoint monitoring | ✅ | `deployment/kubernetes/blackbox-exporter.yaml` |
| 6.4 | **kube-state-metrics** installed | ⬜ | Required for pod status panel in Grafana |
| 6.5 | **Grafana** installed with dashboard imported | ✅ | `deployment/kubernetes/grafana-dashboard-configmap.yaml` |
| 6.6 | **Certificate expiry alerts** configured | ✅ | 21-day warning, 3-day critical |
| 6.7 | **cert-manager downtime alert** configured | ✅ | `CertManagerAbsent` — 5 min downtime |
| 6.8 | **API health probe** configured | ✅ | Blackbox Probe for /api/health |
| 6.9 | **Log aggregation** (Loki, Elastic, or cloud logging) | ⬜ | Structured JSON logs available |
| 6.10 | **Alertmanager** configured with notifications | ⬜ | Email, Slack, or PagerDuty |

---

## 7. 🚀 CI/CD & Deployments

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 7.1 | **Container images** built and pushed to registry | ⬜ | Docker Hub, ECR, GCR, or similar |
| 7.2 | **Image tags** use versioned tags (not `latest`) | ⬜ | e.g., `v1.2.3` |
| 7.3 | **Image pull policy** set to `IfNotPresent` | ✅ | Defined in `deployment.yaml` |
| 7.4 | **Rolling update** strategy configured | ✅ | maxSurge=1, maxUnavailable=0 |
| 7.5 | **Health checks** (liveness + readiness) configured | ✅ | Probes for backend and frontend |
| 7.6 | **CI pipeline** runs tests + lint before deploy | ⬜ | See `Makefile` for test/lint targets |
| 7.7 | **Dependency vulnerability scanning** | ✅ | `scripts/security_audit.sh` |
| 7.8 | **Secrets scanned** for accidental commits | ⬜ | git-secrets, truffleHog, or similar |
| 7.9 | **Canary or blue/green** deployments for prod | ⬜ | Advanced — for high-traffic deployments |

---

## 8. 📦 Application Configuration

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 8.1 | **ENABLE_HTTPS=true** | ⬜ | Set in `.env` |
| 8.2 | **DOMAIN** set to your actual domain | ⬜ | Replace `your-domain.com` everywhere |
| 8.3 | **JWT_SECRET** set (min 32 chars) | ⬜ | Required when `AUTH_ENABLED=true` |
| 8.4 | **NEXTAUTH_SECRET** set (min 32 chars) | ⬜ | Required for session security |
| 8.5 | **API keys** configured (Gemini, Maps, Weather) | ⬜ | Comma-separated for rotation |
| 8.6 | **PostgreSQL** connection string configured | ⬜ | Not SQLite |
| 8.7 | **Redis** password set | ⬜ | `REDIS_URL=redis://:password@redis:6379/0` |
| 8.8 | **BACKEND_CORS_ORIGINS** includes production domain | ⬜ | https://your-domain.com,https://www.your-domain.com |
| 8.9 | **NEXTAUTH_URL** set to HTTPS domain | ⬜ | https://your-domain.com |
| 8.10 | **SMTP** configured for notifications | ⬜ | If `NOTIFICATIONS_ENABLED=true` |
| 8.11 | **Log level** set to `INFO` (not `DEBUG`) | ✅ | `.env.production` |

---

## 9. 🔄 Resilience & Recovery

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 9.1 | **Pod resource limits** set | ✅ | Backend: 2Gi/1cpu, Frontend: 512Mi/500m |
| 9.2 | **Horizontal Pod Autoscaler** configured | ✅ | CPU >70%, Memory >80% |
| 9.3 | **PodDisruptionBudget** applied | ⬜ | For multi-replica deployments |
| 9.4 | **Backup and restore** tested | ⬜ | Database + model files |
| 9.5 | **Disaster recovery** plan documented | ⬜ | RTO/RPO defined |
| 9.6 | **Readiness probes** configured | ✅ | Backend: /health, Frontend: / |
| 9.7 | **Pod anti-affinity** for multi-replica | ⬜ | Prevents single-node failure |
| 9.8 | **PVC backup** for model storage | ⬜ | Using DVC or cloud storage |

---

## 10. 📝 Documentation & Runbooks

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 10.1 | **Deployment guide** | ✅ | `docs/deployment_guide.md` |
| 10.2 | **API reference** | ✅ | `docs/api_reference.md` |
| 10.3 | **Architecture document** | ✅ | `docs/ARCHITECTURE.md` |
| 10.4 | **API key rotation docs** | ✅ | `docs/API_KEY_ROTATION.md` |
| 10.5 | **Troubleshooting guide** | ✅ | Included in `deployment_guide.md` |
| 10.6 | **TLS deployment runbook** | ✅ | `scripts/deploy_k8s_tls.sh` |
| 10.7 | **Monitoring alerts** documented | ✅ | `deployment/kubernetes/prometheus-rules.yaml` |
| 10.8 | **Env var reference** | ✅ | `.env.production` |

---

## Quick Summary

### Must-Do Before Going Live

```bash
# 1. Generate secrets
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('NEXTAUTH_SECRET=' + secrets.token_urlsafe(32))"

# 2. Configure .env with your domain and secrets
cp .env.production .env
# Edit .env — replace your-domain.com, fill in API keys, set secrets

# 3. Deploy TLS
bash scripts/deploy_k8s_tls.sh your-domain.com

# 4. Deploy monitoring
kubectl apply -f deployment/kubernetes/blackbox-exporter.yaml
kubectl apply -f deployment/kubernetes/prometheus-rules.yaml
kubectl apply -f deployment/kubernetes/grafana-dashboard-configmap.yaml

# 5. Verify
curl https://your-domain.com/api/health
kubectl get certificate -n smart-tire
kubectl get pods -n smart-tire
```

### Legend
- ✅ **Done** — Implemented in the codebase, ready to use
- ⬜ **Action** — You must configure this for your environment
- 🔲 **Optional** — Recommended but not strictly required
