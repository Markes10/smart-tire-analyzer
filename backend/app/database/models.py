"""
Database Models — SQLAlchemy table definitions.
"""

import uuid
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON

from app.config import settings
from app.database.db import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Column-level encryption for user API keys ──────────────────────────────

_FERNET: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return a Fernet cipher derived from JWT_SECRET for encrypting user API keys at rest.
    
    Uses a deterministic derivation so the same plaintext always maps to the same
    ciphertext for a given JWT_SECRET. This is safe because the JWT_SECRET is itself
    a high-entropy secret and is never shared.
    """
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    raw = (settings.JWT_SECRET or "insecure-dev-only-fallback-32-bytes!!").encode("utf-8")
    # Fernet needs a 32-byte url-safe-base64 key; derive via SHA-256
    import base64
    import hashlib
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    _FERNET = Fernet(key)
    return _FERNET


def encrypt_api_key(plaintext: str | None) -> str | None:
    """Encrypt an API key at rest using AES-256 via Fernet."""
    if not plaintext:
        return None
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str | None) -> str | None:
    """Decrypt an API key that was encrypted with encrypt_api_key()."""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


class AnalysisResult(Base):
    """Stores each tire analysis session result."""
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Core predictions
    health_score = Column(Float, nullable=True)
    avg_tread_mm = Column(Float, nullable=True)
    remaining_life_km = Column(Float, nullable=True)
    wear_pattern_label = Column(String(64), nullable=True)
    wear_pattern_severity = Column(String(32), nullable=True)
    risk_level = Column(String(16), nullable=True)
    replace_immediately = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)

    # Full report JSON
    full_report = Column(JSON, nullable=True)

    # Context
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    weather_condition = Column(String(64), nullable=True)

    # Metadata
    tire_brand = Column(String(128), nullable=True)
    tire_model = Column(String(128), nullable=True)
    tire_size = Column(String(32), nullable=True)
    image_filename = Column(String(256), nullable=True)
    model_version = Column(String(32), nullable=True)


class User(Base):
    """Registered user account with encrypted API keys at rest."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    email = Column(String(256), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    # API keys are AES-256-GCM encrypted at rest via Fernet (derived from JWT_SECRET)
    gemini_key_encrypted = Column("gemini_key", String(512), nullable=True)
    mapillary_token_encrypted = Column("mapillary_token", String(512), nullable=True)
    openweather_key_encrypted = Column("openweather_key", String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- Convenience accessors that auto-decrypt ---
    @property
    def gemini_key(self) -> str | None:
        return decrypt_api_key(self.gemini_key_encrypted)

    @gemini_key.setter
    def gemini_key(self, value: str | None) -> None:
        self.gemini_key_encrypted = encrypt_api_key(value)

    @property
    def mapillary_token(self) -> str | None:
        return decrypt_api_key(self.mapillary_token_encrypted)

    @mapillary_token.setter
    def mapillary_token(self, value: str | None) -> None:
        self.mapillary_token_encrypted = encrypt_api_key(value)

    @property
    def openweather_key(self) -> str | None:
        return decrypt_api_key(self.openweather_key_encrypted)

    @openweather_key.setter
    def openweather_key(self, value: str | None) -> None:
        self.openweather_key_encrypted = encrypt_api_key(value)


class FeedbackRecord(Base):
    """Stores user corrections for the continuous learning pipeline."""
    __tablename__ = "feedback_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    feedback_type = Column(String(32), nullable=False)

    # User corrections
    corrected_tread_mm = Column(Float, nullable=True)
    corrected_wear_pattern = Column(String(64), nullable=True)
    corrected_health_score = Column(Float, nullable=True)
    confidence_override = Column(Float, nullable=True)
    comment = Column(Text, nullable=True)

    # Original prediction for diff
    original_prediction = Column(JSON, nullable=True)
    corrected_prediction = Column(JSON, nullable=True)
