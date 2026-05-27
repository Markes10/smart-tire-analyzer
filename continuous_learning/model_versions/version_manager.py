"""
Model Version Manager — Semantic versioning + rollback for Smart Tire models.
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List, cast

logger = logging.getLogger(__name__)

VERSIONS_DIR = Path("continuous_learning/model_versions")
REGISTRY_PATH = Path("ai_model/saved_models/model_registry.json")
SAVED_MODELS_DIR = Path("ai_model/saved_models")
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return cast(Dict[str, Any], data)
    return {"versions": [], "current_version": None, "latest": None}


def save_registry(registry: Dict[str, Any]) -> None:
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def save_new_version(model, metrics: Dict) -> str:
    """
    Save new model as a new version with metadata.
    
    Args:
        model: Keras model to save
        metrics: Validation metrics for this version
    
    Returns:
        New version string (e.g., "1.2.0")
    """
    registry = load_registry()
    versions = registry.get("versions", [])

    # Compute next version
    if versions:
        last_ver = versions[-1]["version"]
        major, minor, patch = map(int, last_ver.split("."))
        new_version = f"{major}.{minor + 1}.0"
    else:
        new_version = "1.0.0"

    # Save model file
    version_dir = VERSIONS_DIR / f"v{new_version}"
    version_dir.mkdir(parents=True, exist_ok=True)
    model_path = str(version_dir / "model.h5")
    model.save_weights(model_path)

    # Save metadata
    metadata = {
        "version": new_version,
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "model_path": model_path,
        "deployed": True,
    }

    # Update registry
    versions.append(metadata)
    registry["versions"] = versions
    registry["current_version"] = new_version
    registry["latest"] = metadata
    save_registry(registry)

    # Update "model_best.h5" symlink
    best_path = SAVED_MODELS_DIR / "model_best.h5"
    model.save_weights(str(best_path))

    logger.info(f"New model version saved: v{new_version} (metrics: {metrics})")
    return new_version


def rollback(target_version: Optional[str] = None) -> bool:
    """
    Rollback to a previous model version.
    
    Args:
        target_version: Version string to rollback to, or None for previous version
    
    Returns:
        True if rollback successful
    """
    registry = load_registry()
    versions = registry.get("versions", [])

    if len(versions) < 2:
        logger.error("Cannot rollback — only one version exists")
        return False

    if target_version:
        target = next((v for v in versions if v["version"] == target_version), None)
        if not target:
            logger.error(f"Version {target_version} not found")
            return False
    else:
        # Rollback to previous version
        target = versions[-2]

    model_path = target.get("model_path")
    if not Path(model_path).exists():
        logger.error(f"Model file not found: {model_path}")
        return False

    # Copy target version to model_best.h5
    shutil.copy(model_path, str(SAVED_MODELS_DIR / "model_best.h5"))
    registry["current_version"] = target["version"]
    save_registry(registry)

    logger.info(f"✅ Rolled back to v{target['version']}")
    return True


def list_versions() -> List[Dict[str, Any]]:
    """List all available model versions."""
    registry = load_registry()
    versions = registry.get("versions")
    if isinstance(versions, list):
        return cast(List[Dict[str, Any]], versions)
    return []
