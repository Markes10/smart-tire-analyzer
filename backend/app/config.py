"""
Centralized configuration with Pydantic validation.

YAML configs are merged with environment variables. Environment variables
always take priority over config file values.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "configs"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _load_yaml(filename: str) -> Dict[str, Any]:
    path = CONFIG_DIR / filename
    if not path.exists():
        logger.warning("Config file not found: %s — using defaults", path)
        return {}
    try:
        import yaml  # type: ignore

        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.error("Failed to load config %s: %s", filename, exc)
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


def _parse_keys(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [part.strip() for part in raw.replace(";", ",").split(",")]
    return [part for part in parts if part]


class AppSettings(BaseSettings):
    """Validated application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # API keys (comma-separated for rotation)
    GEMINI_API_KEYS_RAW: str = Field(default="", validation_alias="GEMINI_API_KEYS")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_MAPS_API_KEYS_RAW: str = Field(default="", validation_alias="GOOGLE_MAPS_API_KEYS")
    OPENWEATHER_API_KEYS_RAW: str = Field(default="", validation_alias="OPENWEATHER_API_KEYS")
    MAPILLARY_API_KEYS_RAW: str = Field(default="", validation_alias="MAPILLARY_API_KEYS")
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3:8b"

    GEMINI_DAILY_QUOTA: int = Field(default=50, ge=1)
    OPENWEATHER_DAILY_QUOTA: int = Field(default=50, ge=1)
    MAPS_DAILY_QUOTA: int = Field(default=50, ge=1)
    MAPILLARY_DAILY_QUOTA: int = Field(default=50, ge=1)

    DATABASE_URL: str = "sqlite+aiosqlite:///./smart_tire.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    API_WORKERS: int = Field(default=1, ge=1)
    BACKEND_CORS_ORIGINS_RAW: str = Field(default="", validation_alias="BACKEND_CORS_ORIGINS")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    AUTH_ENABLED: bool = False
    API_KEY: str = ""
    JWT_SECRET: str = "smart-tire-local-demo-secret"
    JWT_ISSUER: str = "smart-tire-analyzer"

    MODEL_PATH: str = "ai_model/saved_models/model_latest.tflite"
    FALLBACK_MODEL_PATH: str = "ai_model/saved_models/model_v1.h5"
    CONFIDENCE_THRESHOLD: float = Field(default=0.65, ge=0.0, le=1.0)
    BLUR_THRESHOLD: float = Field(default=60.0, ge=0.0)

    RETRAIN_THRESHOLD: int = Field(default=10, ge=1)
    MIN_HOURS_BETWEEN_RETRAIN: int = Field(default=24, ge=0)
    AUTO_RETRAIN: bool = True

    LEGAL_MINIMUM_MM: float = 1.6
    WARNING_THRESHOLD_MM: float = 3.0
    TREAD_MAX_MM: float = 12.0
    HEALTH_SCORE_MAX: float = 10.0
    MAX_REMAINING_KM: float = 80000.0
    MAX_IMAGE_SIZE_MB: int = Field(default=10, ge=1, le=50)

    IMAGE_OPTIMIZER_ENABLED: bool = True
    IMAGE_OPTIMIZER_MAX_DIMENSION: int = Field(default=2048, ge=256, le=8192)

    NOTIFICATIONS_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL_FROM: str = "smart-tire@localhost"
    NOTIFICATION_EMAIL_TO: str = ""
    SLACK_WEBHOOK_URL: str = ""
    NOTIFICATION_WEBHOOK_URL: str = ""

    @field_validator("GEMINI_API_KEYS_RAW", mode="before")
    @classmethod
    def _fallback_gemini_key(cls, value: Any) -> str:
        raw = str(value or "")
        if raw:
            return raw
        return os.getenv("GEMINI_API_KEY", "")

    @field_validator("GOOGLE_MAPS_API_KEYS_RAW", mode="before")
    @classmethod
    def _fallback_maps_key(cls, value: Any) -> str:
        raw = str(value or "")
        if raw:
            return raw
        return os.getenv("GOOGLE_MAPS_API_KEY", "")

    @field_validator("OPENWEATHER_API_KEYS_RAW", mode="before")
    @classmethod
    def _fallback_weather_key(cls, value: Any) -> str:
        raw = str(value or "")
        if raw:
            return raw
        return os.getenv("OPENWEATHER_API_KEY", "")

    @field_validator("MAPILLARY_API_KEYS_RAW", mode="before")
    @classmethod
    def _fallback_mapillary_key(cls, value: Any) -> str:
        raw = str(value or "")
        if raw:
            return raw
        return os.getenv("MAPILLARY_API_KEY", "")

    @field_validator("OLLAMA_BASE_URL", mode="before")
    @classmethod
    def _fallback_ollama_host(cls, value: Any) -> str:
        raw = str(value or "")
        if raw:
            return raw
        return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    @field_validator("DEBUG", "AUTH_ENABLED", "AUTO_RETRAIN", "IMAGE_OPTIMIZER_ENABLED", "NOTIFICATIONS_ENABLED", mode="before")
    @classmethod
    def _parse_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}

    def get_gemini_keys(self) -> List[str]:
        return _parse_keys(self.GEMINI_API_KEYS_RAW)

    def get_maps_keys(self) -> List[str]:
        return _parse_keys(self.GOOGLE_MAPS_API_KEYS_RAW)

    def get_weather_keys(self) -> List[str]:
        return _parse_keys(self.OPENWEATHER_API_KEYS_RAW)

    def get_mapillary_keys(self) -> List[str]:
        return _parse_keys(self.MAPILLARY_API_KEYS_RAW)

    def get_cors_origins(self) -> List[str]:
        origins = _parse_keys(self.BACKEND_CORS_ORIGINS_RAW)
        return origins or ["*"]

    def has_gemini(self) -> bool:
        return len(self.get_gemini_keys()) > 0

    def has_maps(self) -> bool:
        return len(self.get_maps_keys()) > 0

    def has_weather(self) -> bool:
        return len(self.get_weather_keys()) > 0

    def has_mapillary(self) -> bool:
        return len(self.get_mapillary_keys()) > 0

    def get_feature_flags(self) -> Dict[str, bool]:
        return {
            "gemini_reasoning": self.has_gemini(),
            "maps_context": self.has_maps(),
            "weather_context": self.has_weather(),
            "mapillary_context": self.has_mapillary(),
            "auto_retrain": self.AUTO_RETRAIN,
            "auth_enabled": self.AUTH_ENABLED,
            "image_optimizer": self.IMAGE_OPTIMIZER_ENABLED,
            "notifications": self.NOTIFICATIONS_ENABLED,
        }

    def log_startup_config(self) -> None:
        flags = self.get_feature_flags()
        logger.info("=== Smart Tire Analyzer Configuration ===")
        logger.info("  Database:     %s", self.DATABASE_URL.split("://")[0])
        logger.info("  Model path:   %s", self.MODEL_PATH)
        logger.info("  Blur thresh:  %s", self.BLUR_THRESHOLD)
        logger.info("  Conf thresh:  %s", self.CONFIDENCE_THRESHOLD)
        logger.info("")
        logger.info("API Key Configuration (Rotation):")
        logger.info(
            "  Gemini:       %d keys (%d req/day each)",
            len(self.get_gemini_keys()),
            self.GEMINI_DAILY_QUOTA,
        )
        logger.info(
            "  Maps:         %d keys (%d req/day each)",
            len(self.get_maps_keys()),
            self.MAPS_DAILY_QUOTA,
        )
        logger.info(
            "  Weather:      %d keys (%d req/day each)",
            len(self.get_weather_keys()),
            self.OPENWEATHER_DAILY_QUOTA,
        )
        logger.info(
            "  Mapillary:    %d keys (%d req/day each)",
            len(self.get_mapillary_keys()),
            self.MAPILLARY_DAILY_QUOTA,
        )
        logger.info("")
        for feature, enabled in flags.items():
            status = "enabled" if enabled else "disabled"
            logger.info("  [%s] %s", status, feature)
        logger.info("==========================================")


# Backward-compatible alias used across the codebase.
Settings = AppSettings
settings = AppSettings()
