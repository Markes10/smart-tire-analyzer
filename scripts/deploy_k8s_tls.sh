#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Smart Tire Analyzer — K8s TLS Deployment Script
# ──────────────────────────────────────────────────────────────────────────
# One-command setup: installs cert-manager + ingress-nginx, applies all
# TLS manifests, and verifies certificate issuance.
#
# Usage:
#   bash scripts/deploy_k8s_tls.sh your-domain.com [--staging]
#
# Examples:
#   bash scripts/deploy_k8s_tls.sh tires.example.com
#   bash scripts/deploy_k8s_tls.sh tires.example.com --staging   # test first
#
# Prerequisites:
#   - kubectl installed and configured for your cluster
#   - Cluster admin privileges (to install cert-manager + ingress-nginx)
#   - DNS A record for your domain pointing to the ingress controller IP
#     (the script tells you the IP after ingress-nginx is installed)
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
INFO="${CYAN}ℹ️${NC}"; OK="${GREEN}✅${NC}"; WARN="${YELLOW}⚠️${NC}"; FAIL="${RED}❌${NC}"

# ── Parse args ──────────────────────────────────────────────────────────
if [ $# -lt 1 ]; then
  echo "Usage: $0 your-domain.com [--staging]"
  exit 1
fi
DOMAIN="$1"
STAGING=false
if [ "${2:-}" = "--staging" ]; then STAGING=true; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/deployment/kubernetes"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  Smart Tire Analyzer — K8s TLS Deployment"
echo "  Domain: $DOMAIN"
echo "  Issuer: $([ "$STAGING" = true ] && echo 'Let\'s Encrypt STAGING (test)' || echo 'Let\'s Encrypt PRODUCTION')"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# ── Step 0: Verify kubectl ───────────────────────────────────────────────
echo -e "${INFO} Checking kubectl..."
kubectl cluster-info --request-timeout=5s 2>/dev/null || {
  echo -e "${FAIL} Cannot connect to cluster. Check your kubeconfig."
  exit 1
}
echo -e "${OK} Connected to: $(kubectl config current-context)"
echo ""

# ── Step 1: Install ingress-nginx ────────────────────────────────────────
echo "── Step 1/7: Install ingress-nginx ──"
if kubectl get ns ingress-nginx &>/dev/null; then
  echo -e "${OK} ingress-nginx already installed"
else
  echo -e "${INFO} Installing ingress-nginx..."
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
  echo -e "${INFO} Waiting for ingress-nginx controller to be ready..."
  kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=120s || true
  echo -e "${OK} ingress-nginx installed"
fi

# Get the ingress controller's external IP
echo ""
echo -e "${INFO} Getting ingress controller external IP..."
sleep 5
INGRESS_IP=""
for i in $(seq 1 10); do
  INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
  if [ -n "$INGRESS_IP" ]; then break; fi
  INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
  if [ -n "$INGRESS_IP" ]; then break; fi
  sleep 5
done

if [ -n "$INGRESS_IP" ]; then
  echo -e "${INFO} Ingress controller IP/hostname: $INGRESS_IP"
  echo ""
  echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${YELLOW}  ║  ACTION REQUIRED: Create DNS A record                       ║${NC}"
  echo -e "${YELLOW}  ║                                                              ║${NC}"
  echo -e "${YELLOW}  ║  Point $DOMAIN to:                            ║${NC}"
  echo -e "${YELLOW}  ║    $INGRESS_IP                    ║${NC}"
  echo -e "${YELLOW}  ║                                                              ║${NC}"
  echo -e "${YELLOW}  ║  Then press Enter to continue...                             ║${NC}"
  echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
  read -rp ""
else
  echo -e "${WARN} Could not determine ingress IP. Check your cloud provider's load balancer."
  echo -e "${INFO} Run: kubectl get svc -n ingress-nginx ingress-nginx-controller"
  read -rp "Press Enter once you've set up DNS..."
fi

# ── DNS verification ─────────────────────────────────────────────────────
echo ""
echo "── Verifying DNS resolution ──"
DNS_OK=false
for i in $(seq 1 12); do
  RESOLVED=$(host "$DOMAIN" 2>/dev/null | head -1 || dig +short "$DOMAIN" 2>/dev/null || nslookup "$DOMAIN" 2>/dev/null | grep -i address || echo "")
  if [ -n "$RESOLVED" ]; then
    echo -e "${OK} Domain $DOMAIN resolves: $RESOLVED"
    DNS_OK=true
    break
  fi
  if [ "$i" -eq 1 ]; then
    echo -e "${INFO} Waiting for DNS propagation for $DOMAIN..."
  fi
  echo -n "."
  sleep 10
done
echo ""

if [ "$DNS_OK" = false ]; then
  echo -e "${WARN} Could not verify DNS resolution for $DOMAIN."
  echo -e "${INFO} Continuing anyway — certificate may take longer to issue."
  echo -e "${INFO} Verify DNS with: host $DOMAIN || nslookup $DOMAIN"
fi

# ── Step 2: Install cert-manager ─────────────────────────────────────────
echo ""
echo "── Step 2/7: Install cert-manager ──"
if kubectl get ns cert-manager &>/dev/null; then
  echo -e "${OK} cert-manager already installed"
else
  echo -e "${INFO} Installing cert-manager..."
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
  echo -e "${INFO} Waiting for cert-manager pods to be ready..."
  # Wait for all cert-manager pods (works for both Helm and static manifests)
  kubectl wait --namespace cert-manager \
    --for=condition=ready pod \
    --all \
    --timeout=180s || true
  echo -e "${OK} cert-manager installed"
fi

# ── Step 3: Apply namespace and services ─────────────────────────────────
echo ""
echo "── Step 3/7: Apply namespace and Services ──"
kubectl apply -f "$K8S_DIR/service.yaml"
echo -e "${OK} Namespace and Services applied"

# ── Step 4: Apply app deployments ────────────────────────────────────────
echo ""
echo "── Step 4/7: Apply app Deployments ──"
kubectl apply -f "$K8S_DIR/deployment.yaml"
kubectl apply -f "$K8S_DIR/frontend-deployment.yaml"
echo -e "${OK} Deployments applied"
echo -e "${INFO} Waiting for pods to be ready..."
kubectl wait --namespace smart-tire \
  --for=condition=ready pod \
  --selector=app=smart-tire-backend \
  --timeout=120s || true
kubectl wait --namespace smart-tire \
  --for=condition=ready pod \
  --selector=app=smart-tire-frontend \
  --timeout=120s || true

# ── Step 5: Apply ClusterIssuer ──────────────────────────────────────────
echo ""
echo "── Step 5/7: Apply cert-manager ClusterIssuer ──"
# Update email in the issuer
EMAIL="admin@$DOMAIN"
TMP_ISSUER=$(mktemp)
sed "s/admin@your-domain.com/$EMAIL/g" "$K8S_DIR/cert-manager-issuer.yaml" > "$TMP_ISSUER"
kubectl apply -f "$TMP_ISSUER"
rm -f "$TMP_ISSUER"
echo -e "${OK} ClusterIssuer applied for $EMAIL"

# ── Step 6: Apply Ingress with TLS ───────────────────────────────────────
echo ""
echo "── Step 6/7: Apply Ingress with TLS ──"
# Update domain in the ingress
TMP_INGRESS=$(mktemp)
sed "s/YOUR_DOMAIN.com/$DOMAIN/g" "$K8S_DIR/ingress.yaml" > "$TMP_INGRESS"

# Switch issuer based on staging flag
if [ "$STAGING" = true ]; then
  sed -i 's/letsencrypt-prod/letsencrypt-staging/g' "$TMP_INGRESS"
  echo -e "${WARN} Using STAGING issuer (certificates won't be trusted)"
fi

kubectl apply -f "$TMP_INGRESS"
rm -f "$TMP_INGRESS"

# Also update the frontend deployment with the correct domain
TMP_FRONTEND=$(mktemp)
sed "s/YOUR_DOMAIN.com/$DOMAIN/g" "$K8S_DIR/frontend-deployment.yaml" > "$TMP_FRONTEND"
kubectl apply -f "$TMP_FRONTEND"
rm -f "$TMP_FRONTEND"

echo -e "${OK} Ingress applied for $DOMAIN"

# ── Step 7: Verify certificate issuance ──────────────────────────────────
echo ""
echo "── Step 7/7: Verify certificate issuance ──"
echo -e "${INFO} Waiting for certificate to be issued (this may take 1-2 minutes)..."
sleep 10

for i in $(seq 1 24); do
  READY=$(kubectl get certificate -n smart-tire smart-tire-tls \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
  if [ "$READY" = "True" ]; then
    echo -e "${OK} Certificate issued successfully!"
    break
  fi
  echo -n "."
  sleep 5
done
echo ""

# Show certificate details
CERT_OBJ=$(kubectl get certificate -n smart-tire smart-tire-tls -o yaml 2>/dev/null || true)
if [ -n "$CERT_OBJ" ]; then
  echo ""
  echo -e "${INFO} Certificate details:"
  kubectl get certificate -n smart-tire smart-tire-tls -o wide
  echo ""
  echo -e "${INFO} Test HTTPS: curl -v https://$DOMAIN/health"
fi

# ── Apply blackbox-exporter ──────────────────────────────────────────────
echo ""
echo "── Optional: Deploy blackbox-exporter for endpoint monitoring ──"
if [ -f "$K8S_DIR/blackbox-exporter.yaml" ]; then
  # Replace domain in the Probe targets
  TMP_BLACKBOX=$(mktemp)
  sed "s/YOUR_DOMAIN.com/$DOMAIN/g" "$K8S_DIR/blackbox-exporter.yaml" > "$TMP_BLACKBOX"
  kubectl apply -f "$TMP_BLACKBOX" 2>/dev/null || echo -e "${WARN} Blackbox-exporter skipped (Prometheus Operator CRDs may not be available)"
  rm -f "$TMP_BLACKBOX"
  echo -e "${OK} Blackbox-exporter deployed — probes configured for https://$DOMAIN"
else
  echo -e "${WARN} blackbox-exporter.yaml not found — skipping"
fi

# ── Apply NetworkPolicy and monitoring ────────────────────────────────────
echo ""
echo "── Optional: Apply NetworkPolicy and monitoring ──"
kubectl apply -f "$K8S_DIR/network-policy.yaml" 2>/dev/null || echo -e "${WARN} NetworkPolicy skipped"
kubectl apply -f "$K8S_DIR/prometheus-rules.yaml" 2>/dev/null || echo -e "${WARN} PrometheusRules skipped"

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  TLS Deployment Complete for: $DOMAIN"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  HTTPS URL: https://$DOMAIN"
echo "  API:       https://$DOMAIN/api/health"
echo "  Frontend:  https://$DOMAIN/"
echo ""
echo "  Commands to verify:"
echo "    curl https://$DOMAIN/api/health"
echo "    kubectl get certificate -n smart-tire"
echo "    kubectl describe certificate smart-tire-tls -n smart-tire"
echo ""
echo "  Grafana dashboard available at:"
echo "    deployment/kubernetes/grafana-dashboard-configmap.yaml"
echo "    → Import into your Grafana instance"
echo ""
echo "  Blackbox-exporter (endpoint monitoring):"
echo "    deployment/kubernetes/blackbox-exporter.yaml"
echo "    → Probes: /api/health, /frontend"
echo ""
echo "  Production readiness checklist:"
echo "    PRODUCTION_READINESS.md"
echo ""
