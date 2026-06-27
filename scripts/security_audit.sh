#!/usr/bin/env bash
# ── Smart Tire Analyzer — Security Audit Script ────────────────────────────
# Run this script to check for known vulnerabilities in dependencies.
#
# Usage:
#   bash scripts/security_audit.sh
#
# Output: prints a report of any vulnerabilities found.
# Requires: pip-audit (Python) and npm (Node.js).

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════"
echo "  Smart Tire Analyzer — Security Audit"
echo "════════════════════════════════════════════════"
echo ""

# ── 1. Python dependency audit ────────────────────────────────────────────
echo "━━━ [1/2] Python dependencies (pip-audit) ━━━"

if command -v pip-audit &>/dev/null; then
    pip-audit --requirement backend/requirements.txt --desc on 2>&1 || true
    echo -e "${GREEN}✅ pip-audit completed${NC}"
else
    echo -e "${YELLOW}⚠️  pip-audit not installed. Install with: pip install pip-audit${NC}"
    echo "   Running basic pip check instead..."
    pip check backend/ 2>&1 || true
fi

echo ""

# ── 2. Frontend npm audit ─────────────────────────────────────────────────
echo "━━━ [2/2] Frontend dependencies (npm audit) ━━━"

if command -v npm &>/dev/null; then
    if [ -f frontend/package-lock.json ]; then
        (cd frontend && npm audit --audit-level=high 2>&1) || true
    else
        echo -e "${YELLOW}⚠️  No package-lock.json found in frontend/${NC}"
    fi
    echo -e "${GREEN}✅ npm audit completed${NC}"
else
    echo -e "${YELLOW}⚠️  npm not installed. Skipping frontend audit.${NC}"
fi

echo ""

# ── 3. Summary ────────────────────────────────────────────────────────────
echo "━━━ Audit Complete ━━━"
echo ""
echo "For continuous security monitoring, consider adding these to CI/CD:"
echo "  - pip-audit (Python deps)"
echo "  - npm audit (JS deps)"
echo "  - truffleHog / git-secrets (secret scanning)"
echo "  - bandit (Python static analysis)"
echo "  - Semgrep / CodeQL (code analysis)"
echo ""
echo "See docs/ for the full security hardening guide."
