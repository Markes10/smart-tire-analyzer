"""Schema loader and helpers for dataset class definitions.

This module exposes simple utilities to load YAML schema files placed
under `dataset/schemas/` and a couple of helpers such as converting
tread depth (mm) to a classification label.

PyYAML is used to parse the schema files; if not installed the loader
gives an informative ImportError.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

BASE_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = BASE_DIR / "schemas"


def _ensure_yaml_available() -> None:
    if yaml is None:
        raise ImportError(
            "PyYAML is required to load schema files. Install with: pip install pyyaml"
        )


def load_schema(name: str) -> Dict[str, Any]:
    """Load a YAML schema from `dataset/schemas/<name>.yaml`.

    Args:
        name: Schema file name with or without the .yaml suffix (e.g. 'tire_condition_classes').

    Returns:
        Parsed YAML as a Python `dict`.
    """
    _ensure_yaml_available()
    fname = name if name.endswith(".yaml") else f"{name}.yaml"
    path = SCHEMAS_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_classes(category: str) -> List[str]:
    """Return the canonical class labels for a given category.

    Works for files that expose a top-level `classes` list or a
    `classification_bins` list containing dicts with a `label`.
    """
    schema = load_schema(category if category.endswith("_classes") else f"{category}_classes")
    if "classes" in schema and isinstance(schema["classes"], list):
        return schema["classes"]
    if "classification_bins" in schema and isinstance(schema["classification_bins"], list):
        return [b.get("label") for b in schema["classification_bins"] if isinstance(b, dict)]
    return []


def mm_to_tread_depth_class(mm: float) -> Optional[str]:
    """Map a numeric tread depth (mm) to the configured classification label.

    The function consults `tread_depth_classes.yaml` in the `schemas/`
    folder. If that file is unavailable, an ImportError will be raised
    by `load_schema`.
    """
    schema = load_schema("tread_depth_classes")
    bins = schema.get("classification_bins", [])
    try:
        # Prefer bins sorted by their lower bound so boundary values map
        # to the expected (lower-range) class when ranges overlap.
        sorted_bins = sorted(
            bins,
            key=lambda b: float(b.get("min_mm", float("-inf"))) if isinstance(b, dict) else float("-inf"),
        )
        for b in sorted_bins:
            min_mm = float(b.get("min_mm", float("-inf")))
            max_mm = float(b.get("max_mm", float("inf")))
            if mm is None:
                continue
            if min_mm <= float(mm) <= max_mm:
                return b.get("label")
    except Exception:
        pass
    # Fallback: best-effort mapping using common thresholds.
    if mm is None:
        return None
    mm = float(mm)
    if mm > 8:
        return "New"
    if 6 <= mm <= 8:
        return "Good"
    if 4 <= mm < 6:
        return "Moderate"
    if 2 <= mm < 4:
        return "Replace Soon"
    return "Dangerous"


def confidence_pct_to_label(pct: float) -> Optional[str]:
    """Map a model confidence percentage to a human label.

    Reads `confidence_classes.yaml` which is expected to contain items
    with `min_pct`/`max_pct` ranges.
    """
    schema = load_schema("confidence_classes")
    classes = schema.get("classes") or []
    try:
        for c in classes:
            minp = float(c.get("min_pct", 0))
            maxp = float(c.get("max_pct", 100))
            if minp <= float(pct) <= maxp:
                return c.get("label")
    except Exception:
        pass
    return None


__all__ = [
    "BASE_DIR",
    "SCHEMAS_DIR",
    "load_schema",
    "get_classes",
    "mm_to_tread_depth_class",
    "confidence_pct_to_label",
]
