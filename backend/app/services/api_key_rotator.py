"""
API Key Rotation Manager — Handles multi-key rotation for Gemini, Weather, and Maps APIs.
Tracks usage per API key and automatically switches to next available key when quota is exceeded.
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class APIKeyUsage:
    """Track usage metrics for a single API key."""
    key: str
    api_type: str  # "gemini", "weather", "maps", etc.
    requests_today: int = 0
    daily_quota: int = 50  # Default: 50 requests/day for Gemini
    last_reset: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_active: bool = True
    error_count: int = 0
    consecutive_errors: int = 0
    max_consecutive_errors: int = 3

    def reset_if_new_day(self):
        """Reset request count if a new day has started."""
        now = datetime.now()
        if (now - self.last_reset).days >= 1:
            self.requests_today = 0
            self.last_reset = now
            self.consecutive_errors = 0

    def is_quota_exceeded(self) -> bool:
        """Check if daily quota is exceeded."""
        self.reset_if_new_day()
        return self.requests_today >= self.daily_quota

    def increment_usage(self):
        """Increment request counter."""
        self.reset_if_new_day()
        self.requests_today += 1
        self.last_used = datetime.now()

    def record_error(self):
        """Record an error and potentially deactivate key if too many consecutive errors."""
        self.consecutive_errors += 1
        self.error_count += 1
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.is_active = False
            logger.warning(
                f"API key {self.key[:10]}... for {self.api_type} "
                f"deactivated after {self.max_consecutive_errors} consecutive errors"
            )

    def reset_error_count(self):
        """Reset error counter after successful request."""
        self.consecutive_errors = 0

    def get_status(self) -> Dict:
        """Get current usage status."""
        self.reset_if_new_day()
        remaining = max(0, self.daily_quota - self.requests_today)
        return {
            "key_preview": f"{self.key[:10]}...",
            "api_type": self.api_type,
            "requests_today": self.requests_today,
            "daily_quota": self.daily_quota,
            "remaining": remaining,
            "is_active": self.is_active,
            "is_quota_exceeded": self.is_quota_exceeded(),
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class APIKeyRotator:
    """
    Manages rotation of multiple API keys for a single service.
    Automatically switches to next available key when quota is exceeded or errors occur.
    """

    def __init__(self, api_type: str, keys: List[str], daily_quota: int = 50):
        """
        Initialize rotator with list of API keys.

        Args:
            api_type: Type of API ("gemini", "weather", "maps", "mapillary")
            keys: List of API keys to rotate through
            daily_quota: Requests allowed per key per day
        """
        self.api_type = api_type
        self.daily_quota = daily_quota
        self.usage_map: Dict[str, APIKeyUsage] = {}
        self.current_index = 0

        # Initialize usage tracking for all keys
        for key in keys:
            if key:  # Skip empty keys
                self.usage_map[key] = APIKeyUsage(
                    key=key,
                    api_type=api_type,
                    daily_quota=daily_quota,
                )

        if not self.usage_map:
            logger.warning(f"No valid API keys provided for {api_type}")

    @property
    def available_keys(self) -> List[str]:
        """Get list of all API keys."""
        return list(self.usage_map.keys())

    @property
    def active_keys(self) -> List[str]:
        """Get list of active (not deactivated) API keys."""
        return [k for k, v in self.usage_map.items() if v.is_active]

    @property
    def available_quota_keys(self) -> List[str]:
        """Get list of keys that still have quota available."""
        return [k for k, v in self.usage_map.items() if v.is_active and not v.is_quota_exceeded()]

    def get_current_key(self) -> Optional[str]:
        """
        Get the current active API key.
        Returns None if no keys are available.
        """
        if not self.active_keys:
            logger.error(f"No active API keys available for {self.api_type}")
            return None

        keys = self.active_keys
        # Find a key with available quota
        for _ in range(len(keys)):
            key = keys[self.current_index % len(keys)]
            if not self.usage_map[key].is_quota_exceeded():
                return key
            self.current_index += 1

        # If all keys are quota-exceeded, return the one with most quota remaining
        logger.warning(
            f"All active API keys for {self.api_type} have exceeded daily quota. "
            "Switching to key with most remaining quota."
        )
        best_key = min(
            keys,
            key=lambda k: self.usage_map[k].requests_today
        )
        return best_key

    def rotate_to_next_key(self) -> Optional[str]:
        """
        Manually rotate to next available key.
        Useful when current key fails.
        """
        if not self.active_keys:
            logger.error(f"No active API keys to rotate to for {self.api_type}")
            return None

        keys = self.active_keys
        self.current_index = (self.current_index + 1) % len(keys)
        return keys[self.current_index]

    def record_successful_request(self, key: str):
        """Record a successful request and increment usage."""
        if key in self.usage_map:
            self.usage_map[key].increment_usage()
            self.usage_map[key].reset_error_count()
            logger.debug(
                f"[{self.api_type}] Request recorded. "
                f"Key {key[:10]}... usage: {self.usage_map[key].requests_today}/{self.daily_quota}"
            )

    def record_error(self, key: str, error_msg: str = ""):
        """Record an error for a key."""
        if key in self.usage_map:
            self.usage_map[key].record_error()
            logger.warning(
                f"[{self.api_type}] Error with key {key[:10]}...: {error_msg}"
            )

    def reactivate_key(self, key: str):
        """Reactivate a previously deactivated key (e.g., after manual fix)."""
        if key in self.usage_map:
            self.usage_map[key].is_active = True
            self.usage_map[key].consecutive_errors = 0
            logger.info(f"[{self.api_type}] Reactivated key {key[:10]}...")

    def reset_all_keys(self):
        """Reset all keys (useful for testing or manual reset)."""
        for usage in self.usage_map.values():
            usage.requests_today = 0
            usage.consecutive_errors = 0
            usage.error_count = 0
        logger.info(f"[{self.api_type}] All keys reset")

    def get_status(self) -> Dict:
        """Get status report for all keys."""
        return {
            "api_type": self.api_type,
            "total_keys": len(self.usage_map),
            "active_keys": len(self.active_keys),
            "current_key": self.get_current_key(),
            "keys": {
                key: usage.get_status()
                for key, usage in self.usage_map.items()
            }
        }

    def log_status(self):
        """Log current status of all keys."""
        status = self.get_status()
        logger.info(f"[{self.api_type}] Status: {status['active_keys']}/{status['total_keys']} active keys")
        for key, key_status in status["keys"].items():
            logger.debug(
                f"  {key_status['key_preview']}: "
                f"{key_status['requests_today']}/{key_status['daily_quota']} "
                f"({'INACTIVE' if not key_status['is_active'] else 'active'})"
            )


# ── Global rotators (initialized in main.py) ────────────────────────────────
_gemini_rotator: Optional[APIKeyRotator] = None
_weather_rotator: Optional[APIKeyRotator] = None
_maps_rotator: Optional[APIKeyRotator] = None
_mapillary_rotator: Optional[APIKeyRotator] = None


def initialize_rotators(
    gemini_keys: List[str],
    weather_keys: List[str],
    maps_keys: List[str],
    mapillary_keys: List[str],
):
    """Initialize all global rotators."""
    global _gemini_rotator, _weather_rotator, _maps_rotator, _mapillary_rotator

    _gemini_rotator = APIKeyRotator("gemini", gemini_keys, daily_quota=50)
    _weather_rotator = APIKeyRotator("weather", weather_keys, daily_quota=50)  # Adjust if needed
    _maps_rotator = APIKeyRotator("maps", maps_keys, daily_quota=50)  # Adjust if needed
    _mapillary_rotator = APIKeyRotator("mapillary", mapillary_keys, daily_quota=50)

    logger.info("✅ API key rotators initialized")
    _gemini_rotator.log_status()
    _weather_rotator.log_status()
    _maps_rotator.log_status()
    _mapillary_rotator.log_status()


def get_gemini_rotator() -> Optional[APIKeyRotator]:
    return _gemini_rotator


def get_weather_rotator() -> Optional[APIKeyRotator]:
    return _weather_rotator


def get_maps_rotator() -> Optional[APIKeyRotator]:
    return _maps_rotator


def get_mapillary_rotator() -> Optional[APIKeyRotator]:
    return _mapillary_rotator
