"""
Setup Environment Script — Creates Python venv, installs deps,
creates directories, generates .env from template.

Usage: python scripts/setup_env.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run(cmd: list, cwd=None, check=True):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check,
                          capture_output=False)


def create_directories():
    """Create all required project directories (new dataset layout)."""
    dirs = [
        "ai_model/saved_models",
        # New dataset layout
        "dataset/raw/tread_images/safe",
        "dataset/raw/tread_images/moderate",
        "dataset/raw/tread_images/replace",
        "dataset/raw/sidewall_images/michelin",
        "dataset/raw/sidewall_images/bridgestone",
        "dataset/raw/sidewall_images/apollo",
        "dataset/raw/sidewall_images/others",
        "dataset/raw/spreadsheet",
        "dataset/processed",
        "dataset/annotations",
        "dataset/splits/train",
        "dataset/splits/validation",
        "dataset/splits/test",
        "dataset/continuous_learning/new_images",
        "dataset/continuous_learning/user_feedback",
        "dataset/continuous_learning/retrain_dataset",
        "logs/training",
        "logs/inference",
        "logs/retraining",
        "logs/errors",
        "continuous_learning/wrong_predictions",
        "continuous_learning/model_versions",
    ]
    print("\n[DIR] Creating project directories...")
    for d in dirs:
        Path(PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)
        print(f"   OK {d}")


def setup_env_file():
    """Copy .env.example to .env if not exists."""
    env_example = PROJECT_ROOT / ".env.example"
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"\n[ENV] Created .env from template — please set your API keys")
    else:
        print(f"\n[ENV] .env already exists")


def create_venv():
    """Create Python virtual environment."""
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        print(f"\n[PY] Virtual environment already exists at .venv")
        return
    print("\n[PY] Creating Python virtual environment...")
    run([sys.executable, "-m", "venv", ".venv"])
    print("   OK .venv created")


def install_deps():
    """Install Python dependencies."""
    print("\n[PKG] Installing Python dependencies...")
    pip = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "pip"
    run([str(pip), "install", "--upgrade", "pip"], check=False)
    run([str(pip), "install", "-r", "backend/requirements.txt"])
    print("   OK Dependencies installed")


def create_model_registry():
    """Initialize empty model registry."""
    registry_path = PROJECT_ROOT / "ai_model" / "saved_models" / "model_registry.json"
    if not registry_path.exists():
        import json
        registry = {
            "versions": [],
            "current_version": None,
            "latest": None,
            "created_at": "2026-04-09",
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        print("\n[DB] Model registry initialized")


def main():
    print("=" * 60)
    print("  Smart Tire Analyzer -- Environment Setup")
    print("=" * 60)
    print(f"  Project root: {PROJECT_ROOT}")

    create_directories()
    setup_env_file()
    create_venv()
    install_deps()
    create_model_registry()

    print("\n" + "=" * 60)
    print("  Setup complete!")
    print()
    print("  Next steps:")
    print("  1. Edit .env and add your API keys")
    print("  2. Add tread images  -> dataset/raw/tread_images/{safe,moderate,replace}/")
    print("  3. Add sidewall imgs -> dataset/raw/sidewall_images/{brand}/")
    print("  4. Fill labels       -> dataset/raw/spreadsheet/dataset.xlsx")
    print("  5. Clean dataset     -> python dataset/preprocessing/clean_dataset.py")
    print("  6. Split dataset     -> python dataset/preprocessing/split_dataset.py")
    print("  7. Validate images   -> python dataset/preprocessing/validate_images.py")
    print("  8. Start server      -> python scripts/start_server.py")
    print("  9. Open API docs     -> http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
