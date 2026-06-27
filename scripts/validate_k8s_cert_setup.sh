#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Smart Tire Analyzer — Kubernetes TLS Certificate Validation Script
# ──────────────────────────────────────────────────────────────────────────
# Validates all prerequisites for K8s TLS/HTTPS are met before
# applying cert-manager and Ingress manifests.
#
# Usage:
#   bash scripts/validate_k8s_cert_setup.sh [--domain your-domain.com]
#
# Options:
#   --domain DOMAIN    Check that DOMAIN is referenced in all necessary files
#   --staging          Validate against the staging ClusterIssuer
#   --verbose          Show detailed certificate information
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed
#   2 — Missing required tools
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Color support ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS="${GREEN}✅ PASS${NC}"
FAIL="${RED}❌ FAIL${NC}"
WARN="${YELLOW}⚠️  WARN${NC}"

# ── Parse arguments ─────────────────────────────────────────────────────
DOMAIN=""
STAGING=false
VERBOSE=false
ERRORS=0
WARNINGS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --staging) STAGING=true; shift ;;
    --verbose) VERBOSE=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/deployment/kubernetes"

echo "═══════════════════════════════════════════════════════════════════"
echo "  Smart Tire Analyzer — K8s TLS Certificate Validation"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# ── Tool checks ─────────────────────────────────────────────────────────
echo "── Checking required tools ──"

check_tool() {
  if command -v "$1" &>/dev/null; then
    echo -e "  $PASS  $1 found: $(which "$1")"
    return 0
  else
    echo -e "  $FAIL  $1 not found"
    ERRORS=$((ERRORS + 1))
    return 1
  fi
}

check_tool kubectl
check_tool openssl

# Find Python (python3 or python)
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    echo -e "  $PASS  Python found: $(which "$cmd")"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo -e "  $FAIL  Python not found (needed for YAML validation)"
  ERRORS=$((ERRORS + 1))
fi

# Check PyYAML availability
if [ -n "$PYTHON" ]; then
  if "$PYTHON" -c "import yaml" 2>/dev/null; then
    echo -e "  $PASS  PyYAML is available"
  else
    echo -e "  $WARN  PyYAML not installed — YAML validation will be skipped"
    WARNINGS=$((WARNINGS + 1))
  fi
fi

echo ""

# ── File existence checks ───────────────────────────────────────────────
echo "── Checking manifest files ──"

check_file() {
  if [ -f "$1" ]; then
    echo -e "  $PASS  $(basename "$1")"
    return 0
  else
    echo -e "  $FAIL  $1 not found"
    ERRORS=$((ERRORS + 1))
    return 1
  fi
}

check_file "$K8S_DIR/cert-manager-issuer.yaml"
check_file "$K8S_DIR/ingress.yaml"
check_file "$K8S_DIR/deployment.yaml"
check_file "$K8S_DIR/frontend-deployment.yaml"
check_file "$K8S_DIR/service.yaml"
check_file "$K8S_DIR/prometheus-rules.yaml"

echo ""

# ── YAML syntax validation ──────────────────────────────────────────────
echo "── Validating YAML syntax ──"

validate_yaml() {
  if [ -z "$PYTHON" ]; then
    return 0  # Skip if Python not available
  fi
  if "$PYTHON" -c "import yaml; yaml.safe_load(open('$1', encoding='utf-8'))" 2>/dev/null; then
    echo -e "  $PASS  $(basename "$1")"
  else
    echo -e "  $FAIL  $(basename "$1") — invalid YAML"
    ERRORS=$((ERRORS + 1))
  fi
}

validate_yaml "$K8S_DIR/cert-manager-issuer.yaml"
validate_yaml "$K8S_DIR/ingress.yaml"
validate_yaml "$K8S_DIR/prometheus-rules.yaml"

echo ""

# ── Domain reference checks ─────────────────────────────────────────────
echo "── Checking domain references ──"

check_domain_in_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi
  if grep -a "YOUR_DOMAIN" "$file" &>/dev/null; then
    WARNINGS=$((WARNINGS + 1))
    if [ -n "$DOMAIN" ]; then
      echo -e "  $WARN  $(basename "$file") has placeholder YOUR_DOMAIN (will replace with $DOMAIN)"
    else
      echo -e "  $WARN  $(basename "$file") has placeholder YOUR_DOMAIN"
    fi
  else
    echo -e "  $PASS  $(basename "$file") — domain references seem configured"
  fi
}

check_domain_in_file "$K8S_DIR/ingress.yaml"
check_domain_in_file "$K8S_DIR/frontend-deployment.yaml"
check_domain_in_file "$K8S_DIR/deployment.yaml"

echo ""

# ── Issuer configuration checks ─────────────────────────────────────────
echo "── Checking certificate issuer config ──"

if [ -f "$K8S_DIR/cert-manager-issuer.yaml" ]; then
  # Check if email is set
  if grep -a "admin@your-domain.com" "$K8S_DIR/cert-manager-issuer.yaml" &>/dev/null; then
    echo -e "  $WARN  ClusterIssuer email is still placeholder 'admin@your-domain.com'"
    WARNINGS=$((WARNINGS + 1))
  else
    echo -e "  $PASS  ClusterIssuer email is configured"
  fi

  # Check which issuer is active in ingress
  if grep -a "letsencrypt-staging" "$K8S_DIR/ingress.yaml" &>/dev/null; then
    echo -e "  ${YELLOW}  ℹ️  Ingress uses STAGING issuer (certs won't be trusted by browsers)${NC}"
  elif grep -a "letsencrypt-prod" "$K8S_DIR/ingress.yaml" &>/dev/null; then
    echo -e "  $PASS  Ingress uses PRODUCTION issuer"
  fi
fi

echo ""

# ── TLS certificate verification (if already issued) ────────────────────
echo "── Checking existing TLS certificates ──"

CERT_DIR="$PROJECT_ROOT/certs"
if [ -f "$CERT_DIR/server.crt" ]; then
  echo -e "  $PASS  Development certificate found: $CERT_DIR/server.crt"
  if [ "$VERBOSE" = true ]; then
    echo ""
    openssl x509 -in "$CERT_DIR/server.crt" -noout -subject -issuer -dates -ext subjectAltName 2>/dev/null | sed 's/^/    /'
    echo ""
  fi
else
  echo -e "  $WARN  No local dev certificate found — generate with: bash scripts/generate_dev_certs.sh"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ── Final summary ───────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════"
echo "  Validation complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
  echo -e "  ${GREEN}All checks passed — ready to deploy TLS!${NC}"
elif [ "$ERRORS" -eq 0 ]; then
  echo -e "  ${YELLOW}$ERRORS errors, $WARNINGS warnings — review warnings before deploying${NC}"
else
  echo -e "  ${RED}$ERRORS errors, $WARNINGS warnings — fix errors before deploying${NC}"
fi

echo ""

if [ -n "$DOMAIN" ]; then
  echo "  Deployment checklist for $DOMAIN:"
  echo "    1. kubectl apply -f deployment/kubernetes/service.yaml"
  echo "    2. kubectl apply -f deployment/kubernetes/deployment.yaml"
  echo "    3. kubectl apply -f deployment/kubernetes/frontend-deployment.yaml"
  echo "    4. kubectl apply -f deployment/kubernetes/cert-manager-issuer.yaml"
  echo "    5. kubectl apply -f deployment/kubernetes/ingress.yaml"
  echo "    6. kubectl apply -f deployment/kubernetes/network-policy.yaml"
  echo "    7. kubectl apply -f deployment/kubernetes/prometheus-rules.yaml"
  echo "    8. Verify: curl https://$DOMAIN/health"
else
  echo "  Re-run with --domain your-domain.com for full validation."
fi

echo ""

if [ "$ERRORS" -gt 0 ]; then
  exit 1
fi
exit 0
