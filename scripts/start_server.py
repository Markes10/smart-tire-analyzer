"""
start_server.py — Cross-platform backend startup script.
Works on Windows, Linux, macOS without any shell differences.
Run: python scripts/start_server.py

This script also checks for TLS certificates and offers to generate
self-signed development certificates if missing.
"""

import os
import sys
import subprocess
from pathlib import Path

# Navigate to the project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

def check_requirements():
    """Check if all required packages are installed."""
    try:
        import fastapi  # noqa: F401
        import sqlalchemy  # noqa: F401
        import uvicorn  # noqa: F401
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("   Run: pip install -r backend/requirements.txt")
        sys.exit(1)

    runtimes = []
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
        runtimes.append("PyTorch + torchvision")
    except ImportError:
        pass

    if runtimes:
        print(f"✅ Core packages found. ML runtime(s): {', '.join(runtimes)}")
    else:
        print("⚠️  Core packages found, but no ML runtime is installed. Synthetic fallback will be used.")

def check_env():
    """Check .env file exists."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        example = PROJECT_ROOT / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_path)
            print("⚠️  Created .env from .env.example — please add your API keys!")
        else:
            print("⚠️  No .env file found — API integrations will use fallback mode.")

def check_certs():
    """Check for TLS certificates and offer to generate them if missing."""
    certs_dir = PROJECT_ROOT / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)
    
    server_crt = certs_dir / "server.crt"
    server_key = certs_dir / "server.key"
    
    if server_crt.exists() and server_key.exists():
        print("✅ TLS certificates found in certs/")
        return
    
    # Check if we should generate (only if ENABLE_HTTPS is set or user wants to)
    enable_https = os.getenv("ENABLE_HTTPS", "false").lower() in ("1", "true", "yes")
    
    if enable_https:
        print("⚠️  ENABLE_HTTPS=true but no TLS certificates found in certs/")
        print("   Run: bash scripts/generate_dev_certs.sh")
        print("   Or run docker compose which auto-generates them.")
    else:
        print("ℹ️  No TLS certificates found (HTTPS not enabled). Running on HTTP.")
        print("   To enable HTTPS:")
        print("     1. bash scripts/generate_dev_certs.sh")
        print("     2. Set ENABLE_HTTPS=true in .env")
        print("     3. Restart with nginx: docker compose -f deployment/docker/docker-compose.yml up nginx")
    
    print()


def create_db_dirs():
    """Ensure data directories exist."""
    dirs = [
        PROJECT_ROOT / "continuous_learning" / "wrong_predictions",
        PROJECT_ROOT / "continuous_learning" / "user_feedback",
        PROJECT_ROOT / "continuous_learning" / "model_versions",
        PROJECT_ROOT / "ai_model" / "saved_models",
        PROJECT_ROOT / "logs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✅ Data directories ready.")

def start_server():
    """Start the FastAPI backend with uvicorn."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"\n🚀 Starting Smart Tire Analyzer API on http://{host}:{port}")
    print("   API Docs: http://localhost:8000/docs\n")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port),
        "--reload",
        "--log-level", "info",
    ]
    os.chdir(BACKEND_DIR)
    subprocess.run(cmd)

if __name__ == "__main__":
    print("=" * 55)
    print("   Smart Tire Analyzer — Backend Server")
    print("=" * 55)
    check_requirements()
    check_env()
    check_certs()
    create_db_dirs()
    start_server()
