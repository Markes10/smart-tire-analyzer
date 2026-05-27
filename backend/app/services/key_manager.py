"""
Simple API key rotator utility.

Usage:
    from app.config import settings
    from app.services.key_manager import get_rotator

    rot = get_rotator('gemini', settings.get_gemini_keys())
    key = rot.get_key()
    rot.report_bad()  # rotate to next key on quota/error

This module provides a thread-safe, in-memory round-robin rotator used
by the backend services to fail over between multiple API keys.
"""
from __future__ import annotations

from threading import Lock
from typing import List, Optional, Dict

_ROTATORS: Dict[str, "ApiKeyRotator"] = {}


class ApiKeyRotator:
    def __init__(self, keys: List[str], name: str = "api"):
        self.name = name
        self.lock = Lock()
        # normalize keys, keep order
        self.keys = [k.strip() for k in keys if k and k.strip()]
        self.index = 0

    def has_keys(self) -> bool:
        return len(self.keys) > 0

    def get_key(self) -> Optional[str]:
        with self.lock:
            if not self.keys:
                return None
            return self.keys[self.index]

    def rotate(self) -> Optional[str]:
        """Advance to the next key and return it (round-robin)."""
        with self.lock:
            if not self.keys:
                return None
            self.index = (self.index + 1) % len(self.keys)
            return self.keys[self.index]

    def report_bad(self) -> Optional[str]:
        """Called when current key should be considered bad (quota/error).
        This simply rotates to the next key and returns it.
        """
        return self.rotate()


def get_rotator(name: str, keys: List[str]) -> ApiKeyRotator:
    """Return a singleton rotator for `name`. If already created, ignores `keys`.
    Callers should pass the canonical key list (from config) on first call.
    """
    if name in _ROTATORS:
        return _ROTATORS[name]
    rot = ApiKeyRotator(keys=keys, name=name)
    _ROTATORS[name] = rot
    return rot
