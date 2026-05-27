"""
Optional local security layer for the Smart Tire Analyzer API.

The project runs open by default for student demos. When AUTH_ENABLED=true,
the FastAPI middleware verifies a compact HMAC-signed JWT-style bearer token
without adding another runtime dependency.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


class SecurityService:
    """Small JWT/RBAC helper used by optional API middleware and dashboard APIs."""

    def __init__(self, secret: str | None = None) -> None:
        self.secret = (secret or settings.JWT_SECRET).encode("utf-8")

    def create_demo_token(
        self,
        *,
        subject: str = "local-demo-user",
        role: str = "technician",
        expires_minutes: int = 120,
    ) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": subject,
            "role": role,
            "iss": settings.JWT_ISSUER,
            "iat": now,
            "exp": now + expires_minutes * 60,
        }
        header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self._sign(f"{header_part}.{payload_part}")
        return f"{header_part}.{payload_part}.{signature}"

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
        parts = token.split(".")
        if len(parts) != 3:
            return {"valid": False, "reason": "Malformed token"}

        header_part, payload_part, signature = parts
        expected_signature = self._sign(f"{header_part}.{payload_part}")
        if not hmac.compare_digest(signature, expected_signature):
            return {"valid": False, "reason": "Invalid token signature"}

        try:
            payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
        except Exception as exc:
            return {"valid": False, "reason": f"Invalid token payload: {exc}"}

        if payload.get("iss") != settings.JWT_ISSUER:
            return {"valid": False, "reason": "Invalid token issuer"}
        if int(payload.get("exp", 0)) < int(time.time()):
            return {"valid": False, "reason": "Token expired"}

        return {"valid": True, "claims": payload}

    def status(self) -> dict[str, Any]:
        return {
            "enabled": settings.AUTH_ENABLED,
            "jwt_authentication": "enabled" if settings.AUTH_ENABLED else "available_optional",
            "oauth2_flow": "password_or_gateway_flow_ready",
            "rbac_roles": ["admin", "ml_engineer", "technician", "viewer"],
            "api_key_authentication": "enabled" if settings.API_KEY else "unset",
            "api_gateway": "middleware_guard" if settings.AUTH_ENABLED else "disabled_for_local_demo",
            "data_encryption": {
                "in_transit": "use_https_or_reverse_proxy_in_production",
                "at_rest": "database/file encryption hook documented",
                "secrets": ".env and deployment secrets",
            },
        }

    def _sign(self, signing_input: str) -> str:
        digest = hmac.new(self.secret, signing_input.encode("ascii"), hashlib.sha256).digest()
        return _b64url_encode(digest)
