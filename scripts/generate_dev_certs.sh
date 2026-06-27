#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Smart Tire Analyzer — Development TLS Certificate Generator
# ──────────────────────────────────────────────────────────────────────────
# Generates a self-signed CA + server certificate for local HTTPS development.
#
# Usage:
#   bash scripts/generate_dev_certs.sh
#
# Works on Windows (Git Bash / WSL), Linux, and macOS.
#
# The script creates the following files in the project's certs/ directory:
#   ca.crt          — CA certificate (import into your browser/OS trust store)
#   server.crt      — Server certificate (signed by the local CA)
#   server.key      — Server private key
#   server.pem      — Combined cert+key (used by nginx)
#
# To trust the CA certificate:
#   Windows: double-click certs/ca.crt → Install Certificate →
#            Local Machine → Trusted Root Certification Authorities
#   macOS:   sudo security add-trusted-cert -d -r trustRoot \
#              -k /Library/Keychains/System.keychain certs/ca.crt
#   Linux:   sudo cp certs/ca.crt /usr/local/share/ca-certificates/ \
#              && sudo update-ca-certificates
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"
DAYS_VALID=3650  # 10 years for dev certs

mkdir -p "$CERTS_DIR"

CA_KEY="$CERTS_DIR/ca.key"
CA_CRT="$CERTS_DIR/ca.crt"
SERVER_KEY="$CERTS_DIR/server.key"
SERVER_CSR="$CERTS_DIR/server.csr"
SERVER_CRT="$CERTS_DIR/server.crt"
SERVER_PEM="$CERTS_DIR/server.pem"

# Use a temporary config file to avoid MSYS2 path expansion on Windows
TMP_CNF=$(mktemp /tmp/openssl-dev-XXXXXX.cnf 2>/dev/null || echo "${TMPDIR:-/tmp}/openssl-dev-san.cnf")
trap 'rm -f "$TMP_CNF" "${TMP_CNF%.cnf}-ca.cnf" 2>/dev/null || true' EXIT

# ── Step 1: Generate CA key and certificate ──────────────────────────────
if [ ! -f "$CA_KEY" ] || [ ! -f "$CA_CRT" ]; then
  echo "[1/4] Generating local Certificate Authority..."

  # Use config file instead of -subj to avoid path expansion issues on MSYS2/Windows
  cat > "${TMP_CNF%.cnf}-ca.cnf" << CONFIG_CA
[req]
distinguished_name = req_distinguished_name
x509_extensions    = v3_ca
prompt             = no

[req_distinguished_name]
C  = US
ST = California
L  = San Francisco
O  = Smart Tire Analyzer Dev
OU = Development
CN = Smart Tire Dev CA

[v3_ca]
basicConstraints       = critical, CA:TRUE
keyUsage               = critical, keyCertSign, cRLSign
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always, issuer
CONFIG_CA

  openssl genrsa -out "$CA_KEY" 4096
  openssl req -x509 -new -nodes \
    -key "$CA_KEY" -sha256 -days "$DAYS_VALID" \
    -out "$CA_CRT" \
    -config "${TMP_CNF%.cnf}-ca.cnf"

  echo "  CA certificate: $CA_CRT"
else
  echo "[1/4] CA certificate already exists — skipping"
fi

# ── Step 2: Generate server key ──────────────────────────────────────────
if [ ! -f "$SERVER_KEY" ]; then
  echo "[2/4] Generating server key..."
  openssl genrsa -out "$SERVER_KEY" 2048
else
  echo "[2/4] Server key already exists — skipping"
fi

# ── Step 3: Generate CSR with SANs ───────────────────────────────────────
echo "[3/4] Generating certificate signing request with SANs..."

cat > "$TMP_CNF" << CONFIG
[req]
default_bits        = 2048
distinguished_name  = req_distinguished_name
req_extensions      = req_ext
x509_extensions     = v3_ext
prompt              = no

[req_distinguished_name]
C  = US
ST = California
L  = San Francisco
O  = Smart Tire Analyzer Dev
OU = Development
CN = localhost

[req_ext]
subjectAltName = @alt_names

[v3_ext]
subjectAltName = @alt_names
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature, keyEncipherment
extendedKeyUsage       = serverAuth, clientAuth

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = backend
DNS.4 = frontend
DNS.5 = nginx
IP.1  = 127.0.0.1
IP.2  = ::1
CONFIG

openssl req -new \
  -key "$SERVER_KEY" \
  -out "$SERVER_CSR" \
  -config "$TMP_CNF"

# ── Step 4: Sign the certificate with the CA ─────────────────────────────
echo "[4/4] Signing server certificate with local CA..."
openssl x509 -req \
  -in "$SERVER_CSR" \
  -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$SERVER_CRT" -days "$DAYS_VALID" -sha256 \
  -extfile "$TMP_CNF" -extensions v3_ext

# Create combined PEM for nginx
cat "$SERVER_CRT" "$SERVER_KEY" > "$SERVER_PEM"

# Secure file permissions
chmod 644 "$CA_CRT" "$SERVER_CRT" 2>/dev/null || true
chmod 600 "$SERVER_KEY" "$SERVER_PEM" 2>/dev/null || true

echo ""
echo "✅ Development TLS certificates generated in: $CERTS_DIR"
echo ""
echo "  CA certificate:     $CA_CRT"
echo "  Server certificate: $SERVER_CRT"
echo "  Server key:         $SERVER_KEY"
echo "  Combined PEM:       $SERVER_PEM"
echo ""
echo "  To trust the CA in your browser:"
echo "    Windows: double-click certs/ca.crt → Install Certificate →"
echo "             Local Machine → Trusted Root Certification Authorities"
echo "    macOS:   sudo security add-trusted-cert -d -r trustRoot \\"
echo "               -k /Library/Keychains/System.keychain certs/ca.crt"
echo "    Linux:   sudo cp certs/ca.crt /usr/local/share/ca-certificates/ \\"
echo "               && sudo update-ca-certificates"
echo ""
echo "  Start with: docker compose -f deployment/docker/docker-compose.yml up"
