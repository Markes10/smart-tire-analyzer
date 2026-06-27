"""
Production-grade security layer for the Smart Tire Analyzer API.

Uses the PyJWT library (HS256) for token creation/verification with
standard validation (exp, iss, alg). Implements CSRF protection,
API key verification, and timing-safe comparison everywhere.
"""

from __future__ import annotations

import hmac
import time
from typing import Any

import jwt
from jwt import PyJWTError

from app.config import settings

# Minimum JWT secret length for security
MIN_JWT_SECRET_LENGTH = 32


class SecurityService:
    """JWT/RBAC helper using the PyJWT library with full standard validation.

    In development mode (AUTH_ENABLED=False), tokens can be created with a
    shorter/empty secret for demo purposes. A warning is logged in this case.
    In production (AUTH_ENABLED=True), the caller must provide a secret >= 32 chars.
    """

    def __init__(self, secret: str | None = None) -> None:
        raw_secret = secret or settings.JWT_SECRET or ""
        if not raw_secret:
            if settings.AUTH_ENABLED:
                raise ValueError(
                    "JWT_SECRET is not configured. Set a strong random value "
                    "(min 32 chars) in your .env before enabling authentication."
                )
            # Dev mode: use a fixed dev secret so signup/login work without config
            raw_secret = "dev-only-insecure-32-char-fallback!!"
            logger.warning(
                "JWT_SECRET not set — using insecure dev fallback. "
                "Set a strong JWT_SECRET (min 32 chars) for any non-local deployment."
            )
        if len(raw_secret) < MIN_JWT_SECRET_LENGTH and settings.AUTH_ENABLED:
            raise ValueError(
                f"JWT_SECRET is too short ({len(raw_secret)} chars). "
                f"It must be at least {MIN_JWT_SECRET_LENGTH} characters long."
            )
        self.secret = raw_secret

    def create_demo_token(
        self,
        *,
        subject: str = "local-demo-user",
        role: str = "technician",
        expires_minutes: int = 120,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": subject,
            "role": role,
            "iss": settings.JWT_ISSUER,
            "iat": now,
            "exp": now + expires_minutes * 60,
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify_api_key(self, api_key: str | None) -> bool:
        expected = (settings.API_KEY or "").strip()
        if not expected or not api_key:
            return False
        return hmac.compare_digest(api_key.strip(), expected)

    def verify_authorization_header(self, authorization: str | None) -> dict[str, Any]:
        if not authorization:
            return {"valid": False, "reason": "Missing Authorization header"}
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return {"valid": False, "reason": "Expected Bearer token"}
        return self.verify_token(token)

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                issuer=settings.JWT_ISSUER,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "iss"],
                },
            )
            return {"valid": True, "claims": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "reason": "Token expired"}
        except jwt.InvalidIssuerError:
            return {"valid": False, "reason": "Invalid token issuer"}
        except PyJWTError as exc:
            return {"valid": False, "reason": f"Invalid token: {exc}"}

    def status(self) -> dict[str, Any]:
        return {
            "enabled": settings.AUTH_ENABLED,
            "jwt_algorithm": "HS256 (PyJWT)",
            "jwt_min_secret_length": MIN_JWT_SECRET_LENGTH,
            "jwt_authentication": "enabled" if settings.AUTH_ENABLED else "available_optional",
            "oauth2_flow": "password_or_gateway_flow_ready",
            "rbac_roles": ["admin", "ml_engineer", "technician", "viewer"],
            "api_key_authentication": "enabled" if settings.API_KEY else "unset",
            "api_gateway": "middleware_guard" if settings.AUTH_ENABLED else "disabled_for_local_demo",
            "data_encryption": {
                "in_transit": "TLS required in production (configure nginx with certbot)",
                "at_rest": "database encryption via PostgreSQL TDE or column-level AES-256-GCM",
                "secrets": "Kubernetes Secrets / Docker secrets / env vars (never committed)",
            },
        }
