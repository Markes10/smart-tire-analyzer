#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Smart Tire Analyzer — Production TLS Certificate Setup (Let's Encrypt)
# ──────────────────────────────────────────────────────────────────────────
# This script uses Certbot to obtain and configure Let's Encrypt TLS
# certificates for your production domain.
#
# Prerequisites:
#   1. Your domain (e.g., smart-tire.example.com) must resolve to the
#      public IP of the server where this script runs.
#   2. Port 80 must be open (for ACME HTTP-01 challenge).
#   3. Certbot must be installed:
#        Ubuntu/Debian: sudo apt install certbot
#        macOS:          brew install certbot
#        Windows:        Use WSL with Ubuntu
#
# Usage:
#   bash scripts/setup_production_certs.sh your-domain.com
#
# After running this script:
#   1. The certificates are stored in /etc/letsencrypt/live/your-domain.com/
#   2. Update .env with your domain and enable HTTPS
#   3. Deploy with docker compose
#   4. A systemd timer or cron job is automatically set up for renewal
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Validate arguments ───────────────────────────────────────────────────
if [ $# -lt 1 ]; then
  echo "❌ Usage: $0 <your-domain.com> [--staging]"
  echo ""
  echo "  --staging    Use Let's Encrypt staging server (for testing)"
  echo ""
  echo "Examples:"
  echo "  $0 smart-tire.example.com"
  echo "  $0 smart-tire.example.com --staging   (test without rate limits)"
  exit 1
fi

DOMAIN="$1"
STAGING=""
if [ "${2:-}" = "--staging" ]; then
  STAGING="--staging"
  echo "⚠️  Using Let's Encrypt STAGING server (certificates won't be trusted)"
fi

# ── Check certbot availability ───────────────────────────────────────────
if ! command -v certbot &> /dev/null; then
  echo ""
  echo "❌ certbot is not installed."
  echo ""
  echo "  Install it:"
  echo "    Ubuntu/Debian: sudo apt update && sudo apt install -y certbot"
  echo "    Fedora:        sudo dnf install certbot"
  echo "    macOS:         brew install certbot"
  echo "    RHEL/CentOS:   sudo yum install epel-release && sudo yum install certbot"
  echo ""
  echo "  Then re-run this script."
  exit 1
fi

# ── Obtain certificate ───────────────────────────────────────────────────
echo ""
echo "🔐 Obtaining Let's Encrypt TLS certificate for: $DOMAIN"
echo ""
echo "  This will start a temporary web server on port 80 to prove"
echo "  domain ownership (HTTP-01 ACME challenge)."
echo ""
echo "  Make sure port 80 is open and $DOMAIN resolves to this server."
echo ""

read -rp "Press Enter to continue or Ctrl+C to abort..."

sudo certbot certonly --standalone \
  $STAGING \
  --non-interactive \
  --agree-tos \
  --email "admin@$DOMAIN" \
  --domain "$DOMAIN" \
  --domain "www.$DOMAIN" \
  --rsa-key-size 4096 \
  --preferred-challenges http

CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
  echo "❌ Certificate acquisition failed. Check the error messages above."
  exit 1
fi

# ── Verify certificate ───────────────────────────────────────────────────
echo ""
echo "✅ Certificate obtained successfully!"
echo ""
echo "  Location: $CERT_DIR"
echo "  Fullchain: $CERT_DIR/fullchain.pem"
echo "  Private key: $CERT_DIR/privkey.pem"
echo ""
echo "  Certificate details:"
openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -subject -issuer -dates

# ── Set up auto-renewal ──────────────────────────────────────────────────
# Certbot creates a systemd timer by default. Let's verify it's active.
if systemctl is-active --quiet certbot.timer 2>/dev/null; then
  echo ""
  echo "⏰ Auto-renewal is active (certbot.timer)"
  systemctl status certbot.timer --no-pager 2>/dev/null | head -5
else
  echo ""
  echo "⏰ Setting up cron job for auto-renewal..."
  # Add daily renewal check via cron (works on systems without systemd)    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    COMPOSE_PATH="$PROJECT_ROOT/deployment/docker/docker-compose.yml"
    CRON_JOB="0 3 * * * root certbot renew --quiet --post-hook 'docker compose -f $COMPOSE_PATH restart nginx'"
    if [ -f /etc/crontab ]; then
      if ! grep -q "certbot renew" /etc/crontab 2>/dev/null; then
        echo "$CRON_JOB" | sudo tee -a /etc/crontab > /dev/null
        echo "  Added certbot renewal cron job to /etc/crontab"
      else
        echo "  Certbot renewal cron job already exists"
      fi
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  TLS Setup Complete for: $DOMAIN"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  Update your .env file with:"
echo "    DOMAIN=$DOMAIN"
echo "    ENABLE_HTTPS=true"
echo ""
echo "  The nginx config in docker-compose will mount these certs."
echo ""
echo "  Next deployment:"
echo "    docker compose -f deployment/docker/docker-compose.yml up -d"
echo ""
echo "  Test the HTTPS connection:"
echo "    curl https://$DOMAIN/health"
echo ""
