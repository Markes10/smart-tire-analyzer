"""
Centralized Config Loader — Reads YAML configs and merges with .env overrides.
Provides a single source of truth for all system settings.
"""

import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

# Load .env into os.environ before anything reads os.getenv()
try:
    from dotenv import load_dotenv as _load_dotenv
    # project root is two levels up from backend/app/config.py
    _load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on shell environment

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "configs"


def _load_yaml(filename: str) -> Dict[str, Any]:
    """Load a YAML config file from the configs/ directory.

    Returns a dict on success, or an empty dict on error.
    """
    path = CONFIG_DIR / filename
    if not path.exists():
        logger.warning(f"Config file not found: {path} — using defaults")
        return {}
    try:
        # PyYAML has no bundled stubs in many environments — silence mypy here
        import yaml  # type: ignore
        with open(path) as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load config {filename}: {e}")
        return {}


@lru_cache(maxsize=None)
def get_model_config() -> Dict[str, Any]:
    data = _load_yaml("model_config.yaml").get("model", {})
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=None)
def get_training_config() -> Dict[str, Any]:
    data = _load_yaml("training_config.yaml").get("training", {})
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=None)
def get_api_config() -> Dict[str, Any]:
    return _load_yaml("api_config.yaml")


@lru_cache(maxsize=None)
def get_app_config() -> Dict[str, Any]:
    return _load_yaml("app_config.yaml")


class Settings:
    """
    Central settings object — merges YAML config with environment variable overrides.
    Environment variables always take priority over config file values.
    """

    # ── API Keys ──────────────────────────────────────────────────────────
    # Support multiple keys via comma-separated env vars for rotation/failover
    GEMINI_API_KEYS_RAW: str = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", ""))
    GOOGLE_MAPS_API_KEYS_RAW: str = os.getenv("GOOGLE_MAPS_API_KEYS", os.getenv("GOOGLE_MAPS_API_KEY", ""))
    OPENWEATHER_API_KEYS_RAW: str = os.getenv("OPENWEATHER_API_KEYS", os.getenv("OPENWEATHER_API_KEY", ""))
    MAPILLARY_API_KEYS_RAW: str = os.getenv("MAPILLARY_API_KEYS", os.getenv("MAPILLARY_API_KEY", ""))

    # ── API Daily Quotas (requests per key per day) ─────────────────────
    GEMINI_DAILY_QUOTA: int = int(os.getenv("GEMINI_DAILY_QUOTA", "50"))
    OPENWEATHER_DAILY_QUOTA: int = int(os.getenv("OPENWEATHER_DAILY_QUOTA", "50"))
    MAPS_DAILY_QUOTA: int = int(os.getenv("MAPS_DAILY_QUOTA", "50"))
    MAPILLARY_DAILY_QUOTA: int = int(os.getenv("MAPILLARY_DAILY_QUOTA", "50"))

    @classmethod
    def _parse_keys(cls, raw: str):
        if not raw:
            return []
        # Allow comma- or semicolon-separated lists
        parts = [p.strip() for p in raw.replace(";", ",").split(",")]
        return [p for p in parts if p]

    @classmethod
    def get_gemini_keys(cls):
        return cls._parse_keys(cls.GEMINI_API_KEYS_RAW)

    @classmethod
    def get_maps_keys(cls):
        return cls._parse_keys(cls.GOOGLE_MAPS_API_KEYS_RAW)

    @classmethod
    def get_weather_keys(cls):
        return cls._parse_keys(cls.OPENWEATHER_API_KEYS_RAW)

    @classmethod
    def get_mapillary_keys(cls):
        return cls._parse_keys(cls.MAPILLARY_API_KEYS_RAW)

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./smart_tire.db"
    )

    # ── API Server ─────────────────────────────────────────────────────────
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()

    # ── Model ──────────────────────────────────────────────────────────────
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH", "ai_model/saved_models/model_latest.tflite"
    )
    FALLBACK_MODEL_PATH: str = os.getenv(
        "FALLBACK_MODEL_PATH", "ai_model/saved_models/model_v1.h5"
    )
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
    BLUR_THRESHOLD: float = float(os.getenv("BLUR_THRESHOLD", "100.0"))

    # ── Continuous Learning ────────────────────────────────────────────────
    RETRAIN_THRESHOLD: int = int(os.getenv("RETRAIN_THRESHOLD", "50"))
    MIN_HOURS_BETWEEN_RETRAIN: int = int(os.getenv("MIN_HOURS_BETWEEN_RETRAIN", "24"))
    AUTO_RETRAIN: bool = os.getenv("AUTO_RETRAIN", "true").lower() == "true"

    # ── Tire Safety Thresholds ─────────────────────────────────────────────
    LEGAL_MINIMUM_MM: float = 1.6
    WARNING_THRESHOLD_MM: float = 3.0
    TREAD_MAX_MM: float = 12.0
    HEALTH_SCORE_MAX: float = 10.0
    MAX_REMAINING_KM: float = 80000.0

    # ── Image Validation ───────────────────────────────────────────────────
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))

    @classmethod
    def has_gemini(cls) -> bool:
        return len(cls.get_gemini_keys()) > 0

    @classmethod
    def has_maps(cls) -> bool:
        return len(cls.get_maps_keys()) > 0

    @classmethod
    def has_weather(cls) -> bool:
        return len(cls.get_weather_keys()) > 0

    @classmethod
    def has_mapillary(cls) -> bool:
        return len(cls.get_mapillary_keys()) > 0

    @classmethod
    def get_feature_flags(cls) -> Dict:
        """Return which optional features are available."""
        return {
            "gemini_reasoning": cls.has_gemini(),
            "maps_context":     cls.has_maps(),
            "weather_context":  cls.has_weather(),
            "mapillary_context": cls.has_mapillary(),
            "auto_retrain":     cls.AUTO_RETRAIN,
        }

    @classmethod
    def log_startup_config(cls):
        """Log configuration at startup (without exposing secrets)."""
        flags = cls.get_feature_flags()
        logger.info("=== Smart Tire Analyzer Configuration ===")
        logger.info(f"  Database:     {cls.DATABASE_URL.split('://')[0]}")
        logger.info(f"  Model path:   {cls.MODEL_PATH}")
        logger.info(f"  Blur thresh:  {cls.BLUR_THRESHOLD}")
        logger.info(f"  Conf thresh:  {cls.CONFIDENCE_THRESHOLD}")
        logger.info("")
        logger.info("API Key Configuration (Rotation):")
        logger.info(f"  Gemini:       {len(cls.get_gemini_keys())} keys ({cls.GEMINI_DAILY_QUOTA} req/day each)")
        logger.info(f"  Maps:         {len(cls.get_maps_keys())} keys ({cls.MAPS_DAILY_QUOTA} req/day each)")
        logger.info(f"  Weather:      {len(cls.get_weather_keys())} keys ({cls.OPENWEATHER_DAILY_QUOTA} req/day each)")
        logger.info(f"  Mapillary:    {len(cls.get_mapillary_keys())} keys ({cls.MAPILLARY_DAILY_QUOTA} req/day each)")
        logger.info("")
        for feature, enabled in flags.items():
            status = "✅" if enabled else "❌"
            logger.info(f"  {status} {feature}")
        logger.info("==========================================")



# Singleton
settings = Settings()
